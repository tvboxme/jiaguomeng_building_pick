#!/usr/bin/env python
# encoding: utf-8
# author: 04

from decimal import Decimal as D # noqa


class BufferConsts:

    ALL = 'All'
    ONL = 'Online'
    OFL = 'Offline'
    SGL = 'Single'
    COM = 'Commercial'
    RES = 'Residence'
    IND = 'Industry'
    TRN = 'Train'
    BUFFER_TYPE_OPTIONS = [
        ALL, ONL, OFL, COM, RES, IND, SGL, TRN
    ]
    # 各种加成系数类型
    # general
    E258 = [D(x) for x in ['.2', '.5', '.8', '1.1', '1.4']]
    E234 = [D(x) for x in ['.2', '.3', '.4', '.5', '.6']]
    E246 = [D(x) for x in ['.2', '.4', '.6', '.8', '1.0']]
    E015 = [D('0.75') * x for x in E246]
    E010 = [D('0.5') * x for x in E246]
    E005 = [D('0.25') * x for x in E246]
    # for building bind
    B100 = [D(x) for x in [1, 2, 3, 4, 5]]
    B050 = [D('0.5') * x for x in B100]
    # only for train
    SE010 = [D('0.05') + D('0.25') * x for x in E246]
    COEFFICIENT_OPTIONS = [
        E005, E010, E015, E234, E246, E258,
        B100, B050,
        SE010,
    ]


class BuildingConsts:

    STAR_INCOME = [0, 1, 2, 6, 24, 120]


_B = BufferConsts

# 为了可读性，手写一下，放弃生成

BUILDING_INFO = [{
    'name': '便利店',
    'btype': _B.COM,
    'buffers': [(_B.SGL, _B.B100, '居民楼')]
}, {
    'name': '五金店',
    'btype': _B.COM,
    'buffers': [(_B.SGL, _B.B100, '零件厂')]
}, {
    'name': '服装店',
    'btype': _B.COM,
    'buffers': [(_B.SGL, _B.B100, '纺织厂')]
}, {
    'name': '菜市场',
    'btype': _B.COM,
    'buffers': [(_B.SGL, _B.B100, '食品厂')]
}, {
    'name': '学校',
    'btype': _B.COM,
    'buffers': [(_B.SGL, _B.B100, '图书城')]
}, {
    'name': '图书城',
    'btype': _B.COM,
    'buffers': [(_B.SGL, _B.B100, '学校'), (_B.SGL, _B.B100, '造纸厂')]
}, {
    'name': '商贸中心',
    'btype': _B.COM,
    'buffers': [(_B.SGL, _B.B100, '花园洋房'), (_B.TRN, _B.E010)],
    'fix': 1.022,
}, {
    'name': '加油站',
    'btype': _B.COM,
    'buffers': [(_B.SGL, _B.B050, '人民石油'), (_B.OFL, _B.E010)],
    'fix': 1.2,
}, {
    'name': '民食斋',
    'btype': _B.COM,
    'buffers': [(_B.SGL, _B.B100, '空中别墅'), (_B.ONL, _B.E246)],
    'fix': 1.52,
}, {
    'name': '媒体之声',
    'btype': _B.COM,
    'buffers': [(_B.OFL, _B.E010), (_B.ONL, _B.E005)],
    'fix': 1.615,
}, {
    'name': '木屋',
    'btype': _B.RES,
    'buffers': [(_B.SGL, _B.B100, '木材厂')],
}, {
    'name': '居民楼',
    'btype': _B.RES,
    'buffers': [(_B.SGL, _B.B100, '便利店')],
}, {
    'name': '钢结构房',
    'btype': _B.RES,
    'buffers': [(_B.SGL, _B.B100, '钢铁厂')],
}, {
    'name': '平房',
    'btype': _B.RES,
    'buffers': [(_B.RES, _B.E246)],
    'fix': 1.097
}, {
    'name': '小型公寓',
    'btype': _B.RES,
    'buffers': [(_B.TRN, _B.E234)],
}, {
    'name': '人才公寓',
    'btype': _B.RES,
    'buffers': [(_B.ONL, _B.E246), (_B.IND, _B.E015)],
    'fix': 1.4
}, {
    'name': '花园洋房',
    'btype': _B.RES,
    'buffers': [(_B.SGL, _B.B100, '商贸中心'), (_B.TRN, _B.E010)],
    'fix': 1.022
}, {
    'name': '中式小楼',
    'btype': _B.RES,
    'buffers': [(_B.ONL, _B.E246), (_B.RES, _B.E015)],
    'fix': 1.4
}, {
    'name': '空中别墅',
    'btype': _B.RES,
    'buffers': [(_B.ONL, _B.E246), (_B.SGL, _B.B100, '民食斋')],
    'fix': 1.52
}, {
    'name': '复兴公馆',
    'btype': _B.RES,
    'buffers': [(_B.OFL, _B.E010), (_B.TRN, _B.E010)],
}, {
    'name': '木材厂',
    'btype': _B.IND,
    'buffers': [(_B.SGL, _B.B100, '木屋')],
}, {
    'name': '食品厂',
    'btype': _B.IND,
    'buffers': [(_B.SGL, _B.B100, '菜市场')],
}, {
    'name': '造纸厂',
    'btype': _B.IND,
    'buffers': [(_B.SGL, _B.B100, '图书城')],
}, {
    'name': '水厂',
    'btype': _B.IND,
    'buffers': [(_B.OFL, _B.SE010)],
    'fix': 1.26,
}, {
    'name': '电厂',
    'btype': _B.IND,
    'buffers': [(_B.ONL, _B.E258)],
    'fix': 1.18,
}, {
    'name': '钢铁厂',
    'btype': _B.IND,
    'buffers': [(_B.SGL, _B.B100, '钢结构房'), (_B.IND, _B.E015)],
}, {
    'name': '纺织厂',
    'btype': _B.IND,
    'buffers': [(_B.SGL, _B.B100, '服装店'), (_B.COM, _B.E015)],
}, {
    'name': '零件厂',
    'btype': _B.IND,
    'buffers': [(_B.SGL, _B.B100, '五金店'), (_B.SGL, _B.B050, '企鹅机械')],
}, {
    'name': '企鹅机械',
    'btype': _B.IND,
    'buffers': [(_B.SGL, _B.B100, '零件厂'), (_B.ALL, _B.E010)],
    'fix': 1.33
}, {
    'name': '人民石油',
    'btype': _B.IND,
    'buffers': [(_B.SGL, _B.B100, '加油站'), (_B.OFL, _B.E010)],
    'fix': 1.33
}]
