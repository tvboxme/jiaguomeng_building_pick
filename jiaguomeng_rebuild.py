#!/usr/bin/env python
# encoding: utf-8
# author: 04

import operator
import itertools
from decimal import Decimal as D  # noqa
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

    def __init__(self):
        self.building_matrix = BuildingMatrix(BUILDING_INFO)
        self.custom_config = self.read_custom_config()
        self.fill_global_buffer()

    def read_custom_config(self):
        config = yaml.load(open(CUSTOM_FILE_NAME), Loader=yaml.SafeLoader)
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
                    lambda buf: buf.fit_income(building), buffer_list
                ))
                for effects_name, buffer_list in self.global_effects.items()
            }
            global_coefficient = reduce(operator.mul, [
                D(1) + sum([buffer.coefficient for buffer in buffer_list])
                for buffer_list in match_effects.values()
            ])
            building.global_coefficient = global_coefficient

    def print_plan(self, total_score, main_bd, plan):
        print('总加成: {}'.format(total_score))
        print('主建筑: {}'.format(main_bd.name))
        print('建筑列表:')
        if isinstance(plan, dict):
            plan = [plan[line] for line in [Bc.RES, Bc.COM, Bc.IND]]
        for index, cn in enumerate['住宅', '商业', '工业']:
            print('{idt}{cn}:{bds}'.format(
                idt=' ' * 8,
                cn=cn,
                bds=' '.join(bd.name for bd in plan[index])
            ))


class ExplosionMixin(object):
    """ 暴力破解，高消耗
    """

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
        results = PQ(maxsize=4)
        for plan in tqdm(
                search_space,
                total=search_space_size,
                bar_format='{percentage:3.0f}%, {elapsed}<{remaining}|{bar}|{n_fmt}/{total_fmt}, {rate_fmt}{postfix}',
                ncols=80):
            prod = self.explosion_calc(plan)
            results.put((prod[0], prod[1], plan))
            if results.qsize() == 3:
                results.get()
        second_good = results.get()
        first_good = results.get()
        assert results.empty()
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
    """ 按人为思路筛选，可能出现非最佳的陷阱
    """

    def run(self):
        """ 计算并寻找最优解
        计算方式：
        1. 首先确定每个建筑全局加成
        2. 计算每个建筑最高加成建筑的组合,及加成总倍率,确定主力建筑
        3. 排序，确定当前组合情况下的最佳补位建筑
            1. 基于当前组合刷新剩余建筑的可用BUFF
            2. 排序获取最高加成
        """
        self.first_building_plans()

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
                try:
                    plan = self.building_matrix.put(buffer.buffer_from, plan)
                except MatrixCategoryFull:
                    pass
                except MatrixFull:
                    break
                building_effect += buffer.coefficient
            calc_completed.append({
                'building': bd,
                'max_building_effect': building_effect,
                'plan': plan,
            })
        __import__('ipdb').set_trace()


class CalcByExplosion(CalcJiaGuoMeng, ExplosionMixin):
    pass


class CalcByPick(CalcJiaGuoMeng, PickUpMixin):
    pass


@click.command()
@click.option('-b', '--bomm', is_flag=True, help='Use Explosion Mod.')
def main(bomm):
    if bomm:
        calculater = CalcByExplosion()
        calculater.explosion()
    else:
        calculater = CalcByPick()
        calculater.run()


if __name__ == '__main__':
    main()
