#!/usr/bin/env python
# encoding: utf-8
# author: 04

import copy
from decimal import Decimal as D  # noqa
from consts import BuildingConsts, BufferConsts as Bc
from errors import MatrixFull, MatrixCategoryFull


class Building(object):
    """Every Building in JiaGuoMeng
    """

    def __init__(self, name, btype, buffers, fix=1):
        self.name = name
        self.building_type = btype
        self.buffer_list = self.own_buffer(buffers)
        self.base_fix = D(fix)
        self.bind_to = []
        self.buffed_by = []
        self._bind_effect = None
        self.star = None
        self.result = None

    def __lt__(self, other_bd):
        return self.result < other_bd.result

    def own_buffer(self, buffers):
        for buf in buffers:
            buf.buffer_from = self
        return buffers

    def set_star(self, star):
        self.star = star
        self.self_effect = BuildingConsts.STAR_INCOME[star] * self.base_fix
        for buf in self.buffer_list:
            buf.set_star(star)

    def lookup_bind(self, matrix):
        """绑定建筑关联
        当自身加成时，对自身也绑定
        """
        for buffer in self.buffer_list:
            btype = buffer.buffer_type
            if btype == Bc.SGL:
                building = matrix.buildings.get(buffer.bind_name)
                if building is None:
                    raise ValueError('No Building Names <%s>' % buffer.bind_name)
                self._set_bind(matrix.buildings[buffer.bind_name], buffer)
            if btype in [Bc.ALL, Bc.ONL, Bc.OFL]:
                for bd in matrix.buildings.values():
                    self._set_bind(bd, buffer)
            if btype in [Bc.RES, Bc.COM, Bc.IND]:
                for bd in matrix.indexes[btype]:
                    self._set_bind(bd, buffer)

    def _set_bind(self, bind_building, buffer):
        self.bind_to.append(buffer)
        bind_building.buffed_by.append(buffer)

    def __repr__(self):
        return '<Building:{}|{}星>'.format(
            self.name, self.star if self.star else '未定'
        )


class Buffer(object):

    def __init__(self, buffer_type, coefficient, bind_name=None):
        if buffer_type not in Bc.BUFFER_TYPE_OPTIONS:
            raise ValueError('Buffer type %s is not allowed.' % buffer_type)
        if buffer_type == Bc.SGL and bind_name is None:
            raise ValueError('Single bind should have a bind building.')
        self.buffer_type = buffer_type
        self.bind_name = bind_name
        self.coefficient = coefficient

    def fit_income(self, building, online=True):
        """ 检测此收益加成是否适用于此建筑
        注：火车收益不列入此计算
        """
        btype = self.buffer_type
        if btype in [Bc.IND, Bc.COM, Bc.RES]:
            return btype == building.building_type
        if btype == Bc.ONL:
            return online is True
        if btype == Bc.OFL:
            return online is False
        if btype == Bc.SGL:
            return self.bind_name == building.name
        if btype == Bc.ALL:
            return True
        return False

    def __repr__(self):
        return '<Buffer:{}|{}{}>'.format(
            self.buffer_type, self.coefficient, '-' + self.bind_name if self.bind_name else ''
        )


class GlobalBuffer(Buffer):

    def __init__(self, global_type, buffer_type, coefficient, bind_name=None):
        self.global_type = global_type
        super().__init__(buffer_type, coefficient, bind_name)

    def __repr__(self):
        return '<Buffer:{}-{}|{}{}>'.format(
            self.global_type, self.buffer_type, self.coefficient, '-' + self.bind_name if self.bind_name else ''
        )


class BuildingBuffer(Buffer):

    def __init__(self, buffer_type, coefficient_type, bind_name=None):
        if coefficient_type not in Bc.COEFFICIENT_OPTIONS:
            __import__('ipdb').set_trace()
            raise ValueError('Coeffecient_type %s is not allowed.' % coefficient_type)
        self.coefficient_type = coefficient_type
        self._star = None
        self.buffer_from = None
        super().__init__(buffer_type, None, bind_name)

    def set_star(self, star):
        self._star = star
        self.coefficient = self.coefficient_type[self._star - 1]

    def __unicode__(self):
        return '<Buffer:{}-{}|{}{}>'.format(
            self.buffer_from or '未知来源',
            self.buffer_type,
            self.coefficient if self._star else '未定星',
            '-' + self.bind_name if self.bind_name else ''
        )


class BuildingMatrix(object):

    AREA = {
        Bc.RES: set(),
        Bc.COM: set(),
        Bc.IND: set(),
    }

    def __init__(self, building_config):
        self.buildings = {}
        self.indexes = {
            Bc.IND: [],
            Bc.COM: [],
            Bc.RES: [],
        }
        self.init_building(building_config)

    def init_building(self, building_config):
        """ building_config would like:
        [{
            'name': building_cn_name,
            'type': building_type,
            'buffers': [buiding_buffers],
            'base_fix': 1,
        }]
        method steps:
        1. create all buffer and buildings
        2. link buildings
        """
        for item in building_config:
            item['buffers'] = [
                BuildingBuffer(
                    buf[0], buf[1], bind_name=buf[2] if len(buf) == 3 else None
                )
                for buf in item['buffers']
            ]
            bd = Building(**item)
            self.buildings[bd.name] = bd
            self.indexes[bd.building_type].append(bd)
        for bd in self.buildings.values():
            bd.lookup_bind(self)

    def sort_buffer(self):
        for bd in self.buildings.values():
            bd.buffed_by.sort(key=lambda buf: buf.coefficient, reverse=True)

    def put(self, building, plan=None):
        plan = plan or copy.deepcopy(self.AREA)
        if len(set.union(*plan.values())) >= 9:
            raise MatrixFull()
        target = plan[building.building_type]
        if len(target) >= 3:
            raise MatrixCategoryFull()
        target.add(building)
        return plan
