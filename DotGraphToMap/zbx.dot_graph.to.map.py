import os as m_os
import re as m_re
import json as m_json
from collections import namedtuple as ntuple
from pyzabbix import ZabbixAPI as CZbx

#######################################

dct_opt: dict = {}
str_opt_path: str = m_os.path.splitext(m_os.path.realpath(__file__))[0] + '.json'

with open(str_opt_path, 'r+t') as rd_js:
    dct_opt: dict = m_json.load(rd_js)

#######################################


# # #
# Parse input dot and json
# # #

def _gv_plaintxt_line_parse(str_line_i: str) -> list:
    _gv_plaintxt_line_parse.re_neq_find  = m_re.compile(r'[^\\]"')
    _gv_plaintxt_line_parse.re_wsp_find  = m_re.compile(r'\s')
    _gv_plaintxt_line_parse.re_num_match = m_re.compile(r'-|\d')

    lst_ret: list = []

    num_pos: int = 0

    while num_pos < len(str_line_i):
        if str_line_i[num_pos] == '"':
            num_pos0 = num_pos + 1
            obj_rem = _gv_plaintxt_line_parse.re_neq_find.search(str_line_i, num_pos0)

            if obj_rem is None:
                if str_line_i[num_pos0] != '"':
                    raise ValueError('Unclosed quotation')

                num_pos += 3
                num_pos1 = num_pos0
            else:
                num_pos = obj_rem.end() + 1
                num_pos1 = obj_rem.start() + 1

            lst_ret.append(str_line_i[num_pos0:num_pos1].replace(r'\"', r'"'))
        else:
            num_pos0 = num_pos
            obj_rem = _gv_plaintxt_line_parse.re_wsp_find.search(str_line_i, num_pos)

            if _gv_plaintxt_line_parse.re_num_match.match(str_line_i[num_pos0]) is None:
                if obj_rem is None:
                    lst_ret.append(str_line_i[num_pos:])
                    break
                else:
                    num_pos = obj_rem.end()
                    num_pos1 = obj_rem.start()
                    lst_ret.append(str_line_i[num_pos0:num_pos1])
            else:
                if obj_rem is None:
                    lst_ret.append(float(str_line_i[num_pos:]))
                    break
                else:
                    num_pos = obj_rem.end()
                    num_pos1 = obj_rem.start()
                    lst_ret.append(float(str_line_i[num_pos0:num_pos1]))

    return lst_ret


TZbxEdge = ntuple('TZbxEdge', ['icon', 'edge_d'])

TZbxShape = ntuple('TZbxShape', ['x', 'y', 'width', 'height'])

TGraph = ntuple('TGraph', ['width', 'height', 'node_l', 'edge_l'])

TGNode = ntuple('TGNode', ['name', 'xpoint', 'ypoint', 'width', 'height', 'label', 'zbx_hostid', 'zbx_edge'])

TGEdge = ntuple('TGEdge', ['tail', 'head'])


def input_parse(i_dct_opt: dict) -> object:
    dct_opt = i_dct_opt

    with open(dct_opt['file_json_path'], 'r+t') as rd_js:
        dct_cnn: dict = m_json.load(rd_js)

    obj_node_edge_d: dict = dict([(tpl_kv[0], TZbxEdge(icon=tpl_kv[1]['map_icon_off'], edge_d=tpl_kv[1]['map_edge'])) for tpl_kv in dct_cnn.items()])
    del dct_cnn

    with m_os.popen('neato -T plain-ext "{0}"'.format(dct_opt['file_dot_path'])) as rd:
        str_grtext: str = rd.read()

    num_mode: int = 0

    for str_l in str_grtext.split('\n'):
        lst_gv_attr: list = _gv_plaintxt_line_parse(str_l)

        if num_mode == 0:  # graph
            if lst_gv_attr[0] != 'graph':
                raise ValueError('Invalid data: unknown line prefix.')

            obj_graph: TGraph = TGraph(width=lst_gv_attr[2], height=lst_gv_attr[3], node_l=[], edge_l=[])
            num_mode += 1
        else:
            if lst_gv_attr[0] not in ['node', 'edge', 'stop']:
                raise ValueError('Invalid data: unknown line prefix.')

            if lst_gv_attr[0] == 'node':
                obj_node_edge = obj_node_edge_d[lst_gv_attr[1]]

                if str(lst_gv_attr[1]).startswith('id'):
                    obj_graph.node_l.append(
                        TGNode(
                            name=lst_gv_attr[1]
                            ,xpoint=lst_gv_attr[2]
                            ,ypoint=lst_gv_attr[3]
                            ,width=lst_gv_attr[4]
                            ,height=lst_gv_attr[5]
                            ,label=lst_gv_attr[6]
                            ,zbx_hostid=str(lst_gv_attr[1])[2:]
                            ,zbx_edge=obj_node_edge
                        )
                    )
                else:
                    obj_graph.node_l.append(
                        TGNode(
                            name=lst_gv_attr[1]
                            ,xpoint=lst_gv_attr[2]
                            ,ypoint=lst_gv_attr[3]
                            ,width=lst_gv_attr[4]
                            ,height=lst_gv_attr[5]
                            ,label=lst_gv_attr[6]
                            ,zbx_hostid=None
                            ,zbx_edge=obj_node_edge
                        )
                    )

            if lst_gv_attr[0] == 'edge':
                obj_graph.edge_l.append(TGEdge(tail=lst_gv_attr[1], head=lst_gv_attr[2]))

            if lst_gv_attr[0] == 'stop':
                break

    #for obj_graph_node in obj_graph.node_l:
    #    print(obj_graph_node)

    #print(obj_node_edge_d)
    return obj_graph


# # #
# Creating Zabbix map.
# # #

obj_graph: TGraph = input_parse(dct_opt)
obj_zbx: CZbx = CZbx(dct_opt["zbx_host"])
obj_zbx.login(dct_opt['zbx_login'], dct_opt['zbx_password'])

def _zbxmap_xy_scale_calc(i_obj_graph: TGraph, i_num_scale: int) -> tuple:
    if i_obj_graph.width >= i_obj_graph.height:
        return bool(0), float(i_num_scale / (i_obj_graph.height)) / 2, float(i_num_scale / (i_obj_graph.height)) / 2
    else:
        return bool(1), float(i_num_scale / (i_obj_graph.width)) / 2, float(i_num_scale / (i_obj_graph.width)) / 2


def _zbxmap_calc\
(   i_obj_graph: TGraph
,   i_num_xsc: float
,   i_num_ysc: float
,   i_bln_invertxy: bool
) -> dict:
    if i_bln_invertxy:
        return \
            {   'width' : str(int(i_obj_graph.height * 2 * i_num_ysc))
            ,   'height': str(int(i_obj_graph.width * 2 * i_num_xsc))
            }
    else:
        return \
            {   'height': str(int(i_obj_graph.height * 2 * i_num_ysc))
            ,   'width' : str(int(i_obj_graph.width * 2 * i_num_xsc))
            }


def _zbxmap_shape_calc\
(   i_obj_graph: TGraph
,   i_num_xsc: float
,   i_num_ysc: float
,   i_bln_invertxy: bool
,   i_obj_node: TGNode
) -> dict:
    num_x: int = int((i_obj_graph.width + i_obj_node.xpoint * 0.85) * i_num_xsc)
    num_y: int = int((i_obj_graph.height + i_obj_node.ypoint * 0.85) * i_num_ysc)
    num_w: int = int(i_obj_node.width * i_num_xsc)
    num_h: int = int(i_obj_node.height * i_num_ysc)

    if i_bln_invertxy:
        return {'x': num_y, 'y': num_x, 'width': num_h, 'height': num_w}
    else:
        return {'x': num_x, 'y': num_y, 'width': num_w, 'height': num_h}


TGLineDecor = ntuple('TGLineDecor', ['color', 'drawtype'])


def _opt_line_decor_parse(i_dct_opt_ld: dict) -> dict:
    dct_opt_ld: dict = i_dct_opt_ld.copy()

    for str_key in ['ok', 'ncl', 'inf', 'wrn', 'avg', 'hgh', 'dss']:
        if str_key not in dct_opt_ld:
            dct_opt_ld[str_key] = TGLineDecor(color=None, drawtype=None)
        else:
            dct_opt_ld[str_key] = TGLineDecor\
                (   color=dct_opt_ld[str_key].get('color', None)
                ,   drawtype=dct_opt_ld[str_key].get('drawtype', None))

    return dct_opt_ld


TZbxTrg = ntuple('TZbxTrigger', ['description', 'expression', 'recovery_expression', 'severity'])


def _zbx_trg_find(i_obj_gnode_head: TGNode, i_obj_gnode_tail: TGNode) -> dict:
    if i_obj_gnode_head.zbx_hostid is None:
        return {}

    dct_zbx_trg_filt: dict = i_obj_gnode_head.zbx_edge.edge_d[i_obj_gnode_tail.name]
    str_zitemid_d: dict = {}

    for zbxitem_key_it in dct_zbx_trg_filt['item']:
        dct_zitem_l: list = obj_zbx.item.get(hostids=[i_obj_gnode_head.zbx_hostid], search={'key_': zbxitem_key_it})
        str_zitemid_d.update(dict([(str(dct_zitem['itemid']), str(dct_zitem['key_'])) for dct_zitem in dct_zitem_l]))

    obj_ztrg_d: dict = {}

    for zbxtrg_name_it in dct_zbx_trg_filt['description']:
        for dct_ztrg \
        in obj_zbx.trigger.get(hostids=[i_obj_gnode_head.zbx_hostid], itemids=list(str_zitemid_d.keys()), search={'description': zbxtrg_name_it}):
            for dct_ztrg in obj_zbx.trigger.get(
                        hostids=[i_obj_gnode_head.zbx_hostid]
                    ,   itemids=list(str_zitemid_d.keys())
                    ,   search={'description': zbxtrg_name_it}):

                if str(dct_ztrg['triggerid']) not in obj_ztrg_d:
                    obj_ztrg_d[str(dct_ztrg['triggerid'])] = int(dct_ztrg['priority'])

    return obj_ztrg_d


dct_zmap: dict \
=   {   'name': m_os.path.basename(dct_opt['file_dot_path'])
    ,   'private': 0
    ,   'label_type': 0
    ,   'severity_min': 2
    }

bln_invert_xy, num_xsc, num_ysc = _zbxmap_xy_scale_calc(obj_graph, dct_opt['zbx_map_height'])
dct_zmap.update(_zbxmap_calc(obj_graph, num_xsc, num_ysc, bln_invert_xy))

dct_zmap_node_l: list = []

for num_zmnode_id in range(0, len(obj_graph.node_l)):
    obj_node: TGNode = obj_graph.node_l[num_zmnode_id]

    dct_zmap_node: dict = {'selementid': str(num_zmnode_id), 'label': str(obj_node.label)}

    if obj_node.zbx_hostid is None:
        dct_zmap_node['elementtype'] = 4
    else:
        dct_zmap_node['elementtype'] = 0
        dct_zmap_node['elements'] = [{'hostid': str(obj_node.zbx_hostid)}]

    for dct_zimg in obj_zbx.image.get(output=['imageid', 'name'], search={'name': obj_node.zbx_edge.icon}):
        if dct_zimg['name'] == obj_node.zbx_edge.icon:
            dct_zmap_node['iconid_off'] = str(dct_zimg['imageid'])

    dct_zmap_node.update(_zbxmap_shape_calc(obj_graph, num_xsc, num_ysc, bln_invert_xy, obj_node))
    dct_zmap_node_l.append(dct_zmap_node)

dct_zmap['selements'] = dct_zmap_node_l

dct_opt_ld: dict = _opt_line_decor_parse(dct_opt['line_decor'])
tpl_zbx_trg_severity: tuple = ('ncl', 'inf', 'wrn', 'avg', 'hgh', 'dss')

dct_zmap_edge_l: list = []

for num_idx in range(0, len(obj_graph.edge_l)):
    obj_edge: TGEdge = obj_graph.edge_l[num_idx]

    num_zmnode_id_tail: int = -1
    num_zmnode_id_head: int = -1

    for num_zmnode_id in range(0, len(obj_graph.node_l)):
        obj_node: TGNode = obj_graph.node_l[num_zmnode_id]

        if obj_node.name == obj_edge.tail:
            obj_node_tail: TGNode = obj_node
            num_zmnode_id_tail = num_zmnode_id

        if obj_node.name == obj_edge.head:
            obj_node_head: TGNode = obj_node
            num_zmnode_id_head = num_zmnode_id

    if num_zmnode_id_tail == -1 or num_zmnode_id_head == -1:
        raise ValueError('Tail or head node is not found.')

    dct_zmap_edge: dict = {'selementid1': str(num_zmnode_id_head), 'selementid2': str(num_zmnode_id_tail)}

    if dct_opt_ld['ok'].color is not None:
        dct_zmap_edge['color'] = dct_opt_ld['ok'].color

    dct_zmap_edgetrg_l: list = []

    dct_zbx_trg = _zbx_trg_find(obj_node_head, obj_node_tail)
    dct_zbx_trg.update(_zbx_trg_find(obj_node_tail, obj_node_head))

    for tpl_kv in dct_zbx_trg.items():
        dct_zmap_edgetrg: dict = {'triggerid': str(tpl_kv[0])}
        opt_ld: TGLineDecor = dct_opt_ld[tpl_zbx_trg_severity[tpl_kv[1]]]

        if opt_ld.drawtype is not None:
            dct_zmap_edgetrg['drawtype'] = opt_ld.drawtype

        if opt_ld.color is not None:
            dct_zmap_edgetrg['color'] = str(opt_ld.color)

        dct_zmap_edgetrg_l.append(dct_zmap_edgetrg)

    dct_zmap_edge['linktriggers'] = dct_zmap_edgetrg_l
    dct_zmap_edge_l.append(dct_zmap_edge)

dct_zmap['links'] = dct_zmap_edge_l

''''#!!!DBG: Assertion
with open(r'd:\try.json', 'w+t') as wr_js:
    m_json.dump(dct_zmap, wr_js)
'''

str_zbx_mapid: str = None

for dct_zbx_map in obj_zbx.map.get(output=['sysmapid'], search={'name': dct_zmap['name']}):
    if dct_zbx_map['name'] == dct_zmap['name']:
        str_zbx_mapid = str(dct_zbx_map['sysmapid'][0])

if str_zbx_mapid is None:
    dct_zbx_map = obj_zbx.map.create(**dct_zmap)
else:
    dct_zmap['sysmapid'] = str_zbx_mapid
    dct_zbx_map = obj_zbx.map.update(**dct_zmap)