#!/usr/bin/env python
# encoding: utf-8
# author: 04

import operator
import itertools
from decimal import Decimal as D # noqa
from functools import reduce
from queue import PriorityQueue as PQ # noqa

import yaml
import click
from scipy.special import comb
from tqdm import tqdm

from buildings import BuildingMatrix, GlobalBuffer
from consts import BUILDING_INFO, BufferConsts as Bc
from errors import MatrixCategoryFull, MatrixFull

CUSTOM_FILE_NAME = 'jiaguomeng.yml'


class CalcJiaGuoMeng(object):
    """ 主函数，收集用户信息并完成计算
    """

    def __init__(self, online_mod, conf, only):
        self.building_matrix = BuildingMatrix(BUILDING_INFO)
        self.custom_config = self.read_custom_config(conf)
        self.online_mod = online_mod
        self.only_one_building = only
        self.fill_global_buffer()

    def read_custom_config(self, conf_file):
        config = yaml.load(open(conf_file), Loader=yaml.SafeLoader)
        for config_name in ['1星', '2星', '3星', '4星', '5星']:
            bnames = config[config_name] or ''
            star = int(config_name[:1])
            for name in bnames.split():
                self.building_matrix.buildings[name].set_star(star)
        # 星级全部确定后，可确定所有加成具体数值，即可对buff排序
        self.building_matrix.sort_buffer()
        effect_trans = {
            '政策': 'policy',
            '照片': 'photos',
            '城市任务': 'quests'
        }
        self.global_effects = {
            effect_name: self._read_custom_buffers(effect_name, config[config_name])
            for config_name, effect_name in effect_trans.items()
        }
        self.global_effects['quests'].extend(
            self._read_custom_binds('quests', config['城市任务建筑加成'])
        )

    def _read_custom_buffers(self, global_type, buffer_conf):
        buffer_trans = {
            '在线': Bc.ONL,
            '离线': Bc.OFL,
            '住宅': Bc.RES,
            '商业': Bc.COM,
            '工业': Bc.IND,
        }
        return [
            GlobalBuffer(global_type, buffer_type, D(buffer_conf.get(conf_key)))
            for conf_key, buffer_type in buffer_trans.items()
            if buffer_conf.get(conf_key) is not 0
        ]

    def _read_custom_binds(self, global_type, bind_config):
        return [
            GlobalBuffer(global_type, Bc.SGL, D(coefficient), building_name)
            for building_name, coefficient in bind_config.items()
            if coefficient is not 0
        ]

    def fill_global_buffer(self):
        for building in self.building_matrix.buildings.values():
            match_effects = {
                effects_name: list(filter(
                    lambda buf: buf.fit_income(building, online=self.online_mod), buffer_list
                ))
                for effects_name, buffer_list in self.global_effects.items()
            }
            global_coefficient = reduce(operator.mul, [
                D(1) + sum([buffer.coefficient for buffer in buffer_list])
                for buffer_list in match_effects.values()
            ])
            building.global_coefficient = global_coefficient


class ExplosionMixin(object):
    """ 暴力破解，高消耗
    仅用作验证，不做实际运行使用，未做数据结构简化的优化
    """

    def print_plan(self, total_score, main_bd, plan):
        print('总加成: {}'.format(total_score))
        print('主建筑: {}'.format(main_bd.name))
        print('建筑列表:')
        if isinstance(plan, dict):
            plan = [plan[line] for line in [Bc.RES, Bc.COM, Bc.IND]]
        for index, cn in enumerate(['住宅', '商业', '工业']):
            print('{idt}{cn}:{bds}'.format(
                idt=' ' * 8,
                cn=cn,
                bds=' '.join(bd.name for bd in plan[index])
            ))

    def explosion(self):
        """ 网上的暴力破解方法
        result 最大范围限定为3，随时取出最后一个，即保证前两个是最优化和次优化配置
        """
        _m = self.building_matrix
        res = _m.indexes[Bc.RES]
        com = _m.indexes[Bc.COM]
        ind = _m.indexes[Bc.IND]
        search_space = itertools.product(
            itertools.combinations(res, 3),
            itertools.combinations(com, 3),
            itertools.combinations(ind, 3)
        )
        search_space_size = comb(len(ind), 3) * comb(
            len(com), 3) * comb(len(res), 3)
        print('Total iterations:', search_space_size)
        results = PQ()
        for plan in tqdm(
                search_space,
                total=search_space_size,
                bar_format='{percentage:3.0f}%, {elapsed}<{remaining}|{bar}|{n_fmt}/{total_fmt}, {rate_fmt}{postfix}',
                ncols=80):
            prod = self.explosion_calc(plan)
            results.put((-1 * prod[0], prod[1], plan))
        first_good = results.get()
        second_good = results.get()
        print('The First Good Plan')
        self.print_plan(*first_good)
        print('The Second Good Plan')
        self.print_plan(*second_good)

    def explosion_calc(self, plan):
        plan_buildings = [bd for cat in plan for bd in cat]
        for bd in plan_buildings:
            active_buffers = [
                buffer for buffer in bd.buffed_by
                if buffer.buffer_from in plan_buildings
            ]
            bd.result = (
                D(1) + sum(buf.coefficient for buf in active_buffers)
            ) * bd.global_coefficient
        priority_order = sorted(plan_buildings, key=lambda x: x.result)
        return sum(bd.result for bd in plan_buildings), priority_order[-1]


class PickUpMixin(object):
    """ 按人为思路筛选
    基于最低成本考虑，主建筑总是唯一一个，允许有次升建筑。
    """
    debug = {}

    def run(self):
        """ 计算并寻找最优解
        计算方式：
        1. 首先确定每个建筑全局加成
        2. 计算每个建筑最高加成建筑的组合,及加成总倍率,确定主力建筑
        3. 合并次要方案，并计算总体建筑价值，基于建筑价值排序去除低价值建筑。
        总体建筑价值 = 建筑直接收益系数 + 建筑加成间接收益系数
        4. 输出方案及升级价值排序。
        升级价值 == 建筑直接收益系数
        """
        building_plans = self.first_building_plans()
        self.helper_buildings = [info['bd'] for info in building_plans[30:]]
        main_plan = building_plans[0]
        if self.only_one_building:
            # 一般主力建筑等级高出其他建筑50~100级，高出往期主力建筑20~50级，主力建筑系数调整5倍
            main_plan['bd'].global_coefficient *= 5
        # 执行三次优化, 逐步扩大搜索范围，下探到较差的组合中确认是否有互补情况
        total_income, counted_detail = self.count_total_income(main_plan['plan'])
        consider_plan = confirmed_plan = {
            'plan': main_plan['plan'],
            'total_income': total_income,
            'detail': counted_detail
        }
        seek_ranges = [4, 7, 10]
        for seek_range in seek_ranges:
            value_plans = building_plans[1:seek_range]
            for pick_plan in value_plans:
                merged_plan = self.merge_plans(confirmed_plan['plan'], pick_plan['plan'])
                merge_income, merge_detail = self.count_total_income(merged_plan)
                if merge_income > consider_plan['total_income']:
                    consider_plan = {
                        'plan': merged_plan,
                        'total_income': merge_income,
                        'detail': merge_detail
                    }
            confirmed_plan = consider_plan
        confirmed_plan['sorted_detail'] = sorted([
            (bd, value['direct_income'], value['indirect_income'])
            for bd, value in confirmed_plan['detail'].items()
        ], key=lambda x: x[1] + x[2], reverse=True)
        self.print_plan(confirmed_plan)

    def first_building_plans(self):
        calc_completed = []
        ordered_building_list = sorted(
            self.building_matrix.buildings.values(),
            key=lambda bd: bd.global_coefficient * bd.self_effect,
            reverse=True
        )
        for bd in ordered_building_list:
            plan = self.building_matrix.put(bd)
            building_effect = D(1)
            ordered_buffer_buildings = sorted(bd.buffed_by, key=lambda x: x.coefficient, reverse=True)
            for buffer in ordered_buffer_buildings:
                if not buffer.fit_income(bd, online=self.online_mod):
                    continue
                try:
                    plan = self.building_matrix.put(buffer.buffer_from, plan)
                except MatrixCategoryFull:
                    continue
                except MatrixFull:
                    break
                building_effect += buffer.coefficient
            calc_completed.append({
                'bd': bd,
                'max_bd_effect': building_effect,
                'income_coefficient': bd.global_coefficient * bd.self_effect * building_effect,
                'plan': plan,
            })
        calc_completed.sort(key=lambda x: x['income_coefficient'], reverse=True)
        return calc_completed

    def count_total_income(self, plan, explain=False):
        flat_plan = {
            bd: {
                'direct_income': 0,
                'indirect_income': 0,
            } for line in plan.values() for bd in line}
        explain_data = {}
        for bd, info in flat_plan.items():
            if bd in self.helper_buildings:
                # 辅助建筑只计算间接受益
                continue
            bd_buffed = D(1)
            bd_baseline = bd.global_coefficient * bd.self_effect
            for buf in bd.buffed_by:
                if not buf.fit_income(bd, online=self.online_mod):
                    continue
                if buf.buffer_from in flat_plan:
                    bd_buffed += buf.coefficient
                    flat_plan[buf.buffer_from]['indirect_income'] += (
                        bd_baseline * buf.coefficient)
                    if explain:
                        effect_num = bd_baseline * buf.coefficient
                        bd_explain = explain_data.setdefault(bd, {'buffed_from': [], 'buffer_to': []})
                        bd_explain['buffed_from'].append((buf.buffer_from, effect_num))
                        buffer_from_explain = explain_data.setdefault(buf.buffer_from, {'buffed_from': [], 'buffer_to': []})
                        buffer_from_explain['buffer_to'].append((bd, effect_num))
                        self.debug['explain'] = explain_data
            info['direct_income'] = bd_baseline * bd_buffed
        total_income = sum([info['direct_income'] for info in flat_plan.values()])
        return total_income, flat_plan

    def merge_plans(self, main_plan, pick_plan):
        """ 尝试合并两个plan, 合并后剔除最低加成的建筑
        """
        merging_plan = {key: set.union(main_plan[key], pick_plan[key]) for key in main_plan}
        total_income, detail = self.count_total_income(merging_plan, explain=True)
        for line_name, bd_set in merging_plan.items():
            if len(bd_set) > 3:
                last_bds = sorted(
                    list(bd_set),
                    key=lambda x: detail[x]['direct_income'] + detail[x]['indirect_income'],
                    reverse=True
                )[3:]
                merging_plan[line_name] = bd_set.difference(set(last_bds))
        return merging_plan

    def print_plan(self, confirmed_plan):
        """
        """
        print("建筑方案：")
        bd_types = [('住宅', Bc.RES), ('商业', Bc.COM), ('工业', Bc.IND)]
        for cn, bd_type in bd_types:
            print(f'''{cn}: {''.join([
                '{:<{len}}'.format(bd.name, len=10-len(bd.name)) for bd in confirmed_plan['plan'][bd_type]
            ])}''')
        print('=' * 80)
        titles = ['建筑名称', '直接收益', '间接收益']
        cell_width = 10
        print('建筑价值')
        detail = confirmed_plan['sorted_detail']
        for key in range(3):
            if titles[key] == '建筑名称':
                line = ''.join(['{value:<{len}}'.format(value=value[key].name, len=cell_width - len(value[key].name))
                                for value in detail])
            else:
                line = ''.join(['{value:<{len}.2f}'.format(value=value[key], len=cell_width) for value in detail])
            print(f'''{titles[key]:<4}: {line}''')
        print('=' * 80)
        print('升级优先度')
        print(''.join(
            '{name:<{len}}'.format(
                name=bd.name, len=cell_width - len(bd.name)
            ) for bd, direct, indirect in sorted(detail, key=lambda x:x[1], reverse=True)
            if direct >= indirect
        ))
        print('=' * 80)
        print('总系数')
        print(sum([direct for bd, direct, indirect in detail]))




class CalcByExplosion(CalcJiaGuoMeng, ExplosionMixin):
    pass


class CalcByPick(CalcJiaGuoMeng, PickUpMixin):
    pass


@click.command()
@click.option('-b', '--bomm', is_flag=True, help='Use Explosion Mod.')
@click.option('-f', '--offline', is_flag=True, help='Offline Mod.')
@click.option('-o', '--only', is_flag=True, help='Only One Building is very important!')
@click.option('-c', '--config', default=CUSTOM_FILE_NAME, help='Set conf file path.')
def main(bomm, offline, config, only):
    args = {
        'online_mod': not offline,
        'conf': config,
        'only': only,
    }
    if bomm:
        calculater = CalcByExplosion(**args)
        calculater.explosion()
    else:
        calculater = CalcByPick(**args)
        calculater.run()


if __name__ == '__main__':
    main()
