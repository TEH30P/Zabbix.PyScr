import sys as m_sys
import os as m_os
import re as m_re
import json as m_json

from collections import namedtuple as ntuple
from pyzabbix import ZabbixAPI as CZbx

#######################################

tx_optpath: str = m_os.path.splitext(m_os.path.realpath(__file__))[0] + '.json'

with open(tx_optpath, 'r+t') as rd_js:
    tr_opt: dict = m_json.load(rd_js)

tx_filedot_path: str = m_os.path.abspath(m_sys.argv[1])
tx_filejson_path: str = m_os.path.splitext(tx_filedot_path)[0] + '.json'

#######################################


# # #
# Parse input dot and json
# # #

def _gv_plaintxt_line_parse(i_tx_line: str) -> list:
    re_neq_find  = _gv_plaintxt_line_parse.re_neq_find  = m_re.compile(r'[^\\]"')
    re_wsp_find  = _gv_plaintxt_line_parse.re_wsp_find  = m_re.compile(r'\s')
    re_num_match = _gv_plaintxt_line_parse.re_num_match = m_re.compile(r'-|\d')

    cl_ret: list = []

    nm_pos: int = 0

    while nm_pos < len(i_tx_line):
        if i_tx_line[nm_pos] == '"':
            nm_pos0 = nm_pos + 1
            ob_rem = re_neq_find.search(i_tx_line, nm_pos0)

            if ob_rem is None:
                if i_tx_line[nm_pos0] != '"':
                    raise ValueError('Unclosed quotation')

                nm_pos += 3
                nm_pos1 = nm_pos0
            else:
                nm_pos = ob_rem.end() + 1
                nm_pos1 = ob_rem.start() + 1

            cl_ret.append(i_tx_line[nm_pos0:nm_pos1].replace(r'\"', r'"'))
        else:
            nm_pos0 = nm_pos
            ob_rem = re_wsp_find.search(i_tx_line, nm_pos)

            if re_num_match.match(i_tx_line[nm_pos0]) is None:
                if ob_rem is None:
                    cl_ret.append(i_tx_line[nm_pos:])
                    break
                else:
                    nm_pos = ob_rem.end()
                    nm_pos1 = ob_rem.start()
                    cl_ret.append(i_tx_line[nm_pos0:nm_pos1])
            else:
                if ob_rem is None:
                    cl_ret.append(float(i_tx_line[nm_pos:]))
                    break
                else:
                    nm_pos = ob_rem.end()
                    nm_pos1 = ob_rem.start()
                    cl_ret.append(float(i_tx_line[nm_pos0:nm_pos1]))

    return cl_ret


СZbxEdge = ntuple('TZbxEdge', ['icon', 'edge_d'])

СZbxShape = ntuple('TZbxShape', ['x', 'y', 'width', 'height'])

СGraph = ntuple('TGraph', ['width', 'height', 'node_l', 'edge_l'])

СGNode = ntuple('TGNode', ['name', 'xpoint', 'ypoint', 'width', 'height', 'label', 'zbx_hostid', 'zbx_edge'])

СGEdge = ntuple('TGEdge', ['tail', 'head'])


def _input_parse(i_kv_opt: dict) -> object:
    kv_opt = i_kv_opt

    with open(tx_filejson_path, 'r+t') as rd_js:
        kv_cnn: dict = m_json.load(rd_js)

    ob_node_edge_d: dict = dict([(tpl_kv[0], СZbxEdge(icon=tpl_kv[1]['map_icon_off'], edge_d=tpl_kv[1]['map_edge'])) for tpl_kv in kv_cnn.items()])
    del kv_cnn

    with m_os.popen('{0} -T plain-ext "{1}"'.format(kv_opt['dot_engine'], tx_filedot_path)) as rd:
        tx_grtext: str = rd.read()

    nm_mode: int = 0

    for tx_l in tx_grtext.split('\n'):
        cl_gv_attr: list = _gv_plaintxt_line_parse(tx_l)

        if nm_mode == 0:  # graph
            if cl_gv_attr[0] != 'graph':
                raise ValueError('Invalid data: unknown line prefix.')

            ob_graph: СGraph = СGraph(width=cl_gv_attr[2], height=cl_gv_attr[3], node_l=[], edge_l=[])
            nm_mode += 1
        else:
            if cl_gv_attr[0] not in ['node', 'edge', 'stop']:
                raise ValueError('Invalid data: unknown line prefix.')

            if cl_gv_attr[0] == 'node':
                ob_node_edge = ob_node_edge_d[cl_gv_attr[1]]

                if str(cl_gv_attr[1]).startswith('id'):
                    ob_graph.node_l.append(
                        СGNode(
                            name=cl_gv_attr[1]
                            ,xpoint=cl_gv_attr[2]
                            ,ypoint=cl_gv_attr[3]
                            ,width=cl_gv_attr[4]
                            ,height=cl_gv_attr[5]
                            ,label=cl_gv_attr[6]
                            ,zbx_hostid=str(cl_gv_attr[1])[2:]
                            ,zbx_edge=ob_node_edge
                        )
                    )
                else:
                    ob_graph.node_l.append(
                        СGNode(
                            name=cl_gv_attr[1]
                            ,xpoint=cl_gv_attr[2]
                            ,ypoint=cl_gv_attr[3]
                            ,width=cl_gv_attr[4]
                            ,height=cl_gv_attr[5]
                            ,label=cl_gv_attr[6]
                            ,zbx_hostid=None
                            ,zbx_edge=ob_node_edge
                        )
                    )

            if cl_gv_attr[0] == 'edge':
                ob_graph.edge_l.append(СGEdge(tail=cl_gv_attr[1], head=cl_gv_attr[2]))

            if cl_gv_attr[0] == 'stop':
                break

    return ob_graph


# # #
# Creating Zabbix map.
# # #


def _zbxmap_xy_scale_calc(i_ob_graph: СGraph, i_nm_scale: int) -> tuple:
    if i_ob_graph.width >= i_ob_graph.height:
        return bool(0), float(i_nm_scale / (i_ob_graph.height)) / 2, float(i_nm_scale / (i_ob_graph.height)) / 2
    else:
        return bool(1), float(i_nm_scale / (i_ob_graph.width)) / 2, float(i_nm_scale / (i_ob_graph.width)) / 2


def _zbxmap_calc(
        i_ob_graph: СGraph
    ,   i_nm_xscale: float
    ,   i_nm_yscale: float
    ,   i_bl_invertxy: bool
) -> dict:
    if i_bl_invertxy:
        return \
            {   'width' : str(int(i_ob_graph.height * 2 * i_nm_yscale))
            ,   'height': str(int(i_ob_graph.width * 2 * i_nm_xscale))
            }
    else:
        return \
            {   'height': str(int(i_ob_graph.height * 2 * i_nm_yscale))
            ,   'width' : str(int(i_ob_graph.width * 2 * i_nm_xscale))
            }


def _zbxmap_shape_calc(
        i_ob_graph: СGraph
    ,   i_nm_xscale: float
    ,   i_nm_yscale: float
    ,   i_bl_invertxy: bool
    ,   i_tx_doteng: str
    ,   i_ob_node: СGNode
) -> dict:
    if i_tx_doteng == 'neato':
        nm_x: int = int((i_ob_graph.width + i_ob_node.xpoint * 0.85) * i_nm_xscale)
        nm_y: int = int((i_ob_graph.height + i_ob_node.ypoint * 0.85) * i_nm_yscale)
        nm_w: int = int(i_ob_node.width * i_nm_xscale)
        nm_h: int = int(i_ob_node.height * i_nm_yscale)
    elif i_tx_doteng == 'fdp':
        nm_x: int = int((i_ob_node.xpoint * 1.9) * i_nm_xscale)
        nm_y: int = int((i_ob_node.ypoint * 1.9) * i_nm_yscale)
        nm_w: int = int(i_ob_node.width * i_nm_xscale)
        nm_h: int = int(i_ob_node.height * i_nm_yscale)
    elif i_tx_doteng == 'sfdp':
        nm_x: int = int((i_ob_node.xpoint * 1.9) * i_nm_xscale)
        nm_y: int = int((i_ob_node.ypoint * 1.9) * i_nm_yscale)
        nm_w: int = int(i_ob_node.width * i_nm_xscale)
        nm_h: int = int(i_ob_node.height * i_nm_yscale)
    else:
        raise Exception(f'Graphviz engine "{i_tx_doteng}" is not supported')

    if i_bl_invertxy:
        return {'x': nm_y, 'y': nm_x, 'width': nm_h, 'height': nm_w}
    else:
        return {'x': nm_x, 'y': nm_y, 'width': nm_w, 'height': nm_h}


CGLineDecor = ntuple('TGLineDecor', ['color', 'drawtype'])


def _opt_line_decor_parse(i_kv_opt_ld: dict) -> dict:
    kv_opt_ld: dict = i_kv_opt_ld.copy()

    for tx_key in ['ok', 'ncl', 'inf', 'wrn', 'avg', 'hgh', 'dss']:
        if tx_key not in kv_opt_ld:
            kv_opt_ld[tx_key] = CGLineDecor(color=None, drawtype=None)
        else:
            kv_opt_ld[tx_key] = CGLineDecor\
                (   color=kv_opt_ld[tx_key].get('color', None)
                ,   drawtype=kv_opt_ld[tx_key].get('drawtype', None))

    return kv_opt_ld


def _zbx_trg_find(i_ob_gnode_head: СGNode, i_ob_gnode_tail: СGNode, i_ob_zbxapi: CZbx) -> dict:
    if i_ob_gnode_head.zbx_hostid is None:
        return {}

    kv_zbx_trg_filt: dict = i_ob_gnode_head.zbx_edge.edge_d[i_ob_gnode_tail.name]
    tx_zitemid_kv: dict = {}

    for zbxitem_key_it in kv_zbx_trg_filt['item']:
        kv_zitem_l: list = i_ob_zbxapi.item.get(hostids=[i_ob_gnode_head.zbx_hostid], search={'key_': zbxitem_key_it})
        tx_zitemid_kv.update(dict([(str(kv_zitem['itemid']), str(kv_zitem['key_'])) for kv_zitem in kv_zitem_l]))

    ob_zbxtrigger_d: dict = {}

    for zbxtrigger_name_it in kv_zbx_trg_filt['description']:
        for kv_zbxtrigger \
        in i_ob_zbxapi.trigger.get(
                    hostids=[i_ob_gnode_head.zbx_hostid]
                ,   itemids=list(tx_zitemid_kv.keys())
                ,   search={'description': zbxtrigger_name_it}):
            if str(kv_zbxtrigger['triggerid']) not in ob_zbxtrigger_d:
                ob_zbxtrigger_d[str(kv_zbxtrigger['triggerid'])] = int(kv_zbxtrigger['priority'])

    return ob_zbxtrigger_d


def _zbx_map_create(i_ob_graph: СGraph, i_ob_zbxapi: CZbx) -> None:
    kv_zbx_map_arg: dict \
    =   {   'name': m_os.path.basename(tx_filedot_path)
        ,   'private': 0
        ,   'label_type': 0
        ,   'severity_min': 2
        }

    bl_invertxy, nm_xscale, nm_yscale = _zbxmap_xy_scale_calc(i_ob_graph, tr_opt['zbx_map_height'])
    kv_zbx_map_arg.update(_zbxmap_calc(i_ob_graph, nm_xscale, nm_yscale, bl_invertxy))

    kv_zbxmap_element_cl: list = []

    for nm_zmnode_id in range(0, len(i_ob_graph.node_l)):
        ob_node: СGNode = i_ob_graph.node_l[nm_zmnode_id]

        kv_zmap_node: dict = {'selementid': str(nm_zmnode_id), 'label': str(ob_node.label)}

        if ob_node.zbx_hostid is None:
            kv_zmap_node['elementtype'] = 4
        else:
            kv_zmap_node['elementtype'] = 0
            kv_zmap_node['elements'] = [{'hostid': str(ob_node.zbx_hostid)}]

        for kv_zimg in i_ob_zbxapi.image.get(output=['imageid', 'name'], search={'name': ob_node.zbx_edge.icon}):
            if kv_zimg['name'] == ob_node.zbx_edge.icon:
                kv_zmap_node['iconid_off'] = str(kv_zimg['imageid'])

        kv_zmap_node.update(_zbxmap_shape_calc(i_ob_graph, nm_xscale, nm_yscale, bl_invertxy, tr_opt['dot_engine'], ob_node))
        kv_zbxmap_element_cl.append(kv_zmap_node)

    kv_zbx_map_arg['selements'] = kv_zbxmap_element_cl

    kv_opt_ld: dict = _opt_line_decor_parse(tr_opt['line_decor'])
    tpl_zbx_trg_severity: tuple = ('ncl', 'inf', 'wrn', 'avg', 'hgh', 'dss')

    kv_zbxmap_link_cl: list = []

    for nm_idx in range(0, len(i_ob_graph.edge_l)):
        ob_edge: СGEdge = i_ob_graph.edge_l[nm_idx]

        nm_zmnode_id_tail: int = -1
        nm_zmnode_id_head: int = -1

        for nm_zmnode_id in range(0, len(i_ob_graph.node_l)):
            ob_node: СGNode = i_ob_graph.node_l[nm_zmnode_id]

            if ob_node.name == ob_edge.tail:
                ob_node_tail: СGNode = ob_node
                nm_zmnode_id_tail = nm_zmnode_id

            if ob_node.name == ob_edge.head:
                ob_node_head: СGNode = ob_node
                nm_zmnode_id_head = nm_zmnode_id

        if nm_zmnode_id_tail == -1 or nm_zmnode_id_head == -1:
            raise ValueError('Tail or head node is not found.')

        kv_zbxmap_link: dict = {'selementid1': str(nm_zmnode_id_head), 'selementid2': str(nm_zmnode_id_tail)}

        if kv_opt_ld['ok'].color is not None:
            kv_zbxmap_link['color'] = kv_opt_ld['ok'].color

        kv_zbxmap_linktriger_cl: list = []

        kv_zbxtriger = _zbx_trg_find(ob_node_head, ob_node_tail, i_ob_zbxapi)
        kv_zbxtriger.update(_zbx_trg_find(ob_node_tail, ob_node_head, i_ob_zbxapi))

        for tpl_kv in kv_zbxtriger.items():
            kv_zbxmap_linktriger: dict = {'triggerid': str(tpl_kv[0])}
            opt_ld: CGLineDecor = kv_opt_ld[tpl_zbx_trg_severity[tpl_kv[1]]]

            if opt_ld.drawtype is not None:
                kv_zbxmap_linktriger['drawtype'] = opt_ld.drawtype

            if opt_ld.color is not None:
                kv_zbxmap_linktriger['color'] = str(opt_ld.color)

            kv_zbxmap_linktriger_cl.append(kv_zbxmap_linktriger)

        kv_zbxmap_link['linktriggers'] = kv_zbxmap_linktriger_cl
        kv_zbxmap_link_cl.append(kv_zbxmap_link)

    kv_zbx_map_arg['links'] = kv_zbxmap_link_cl

    ''''#!!!DBG: Assertion
    with open(r'd:\try.json', 'w+t') as wr_js:
        m_json.dump(kv_zbx_map_arg, wr_js)
    '''

    tx_zbx_mapid: str = None

    for kv_zbx_map in i_ob_zbxapi.map.get(output=['sysmapid', 'name'], search={'name': kv_zbx_map_arg['name']}):
        if kv_zbx_map['name'] == kv_zbx_map_arg['name']:
            tx_zbx_mapid = str(kv_zbx_map['sysmapid'][0])

    if tx_zbx_mapid is None:
        kv_zbx_map = i_ob_zbxapi.map.create(**kv_zbx_map_arg)
    else:
        kv_zbx_map_arg['sysmapid'] = tx_zbx_mapid
        kv_zbx_map = i_ob_zbxapi.map.update(**kv_zbx_map_arg)


ob_graph: СGraph = _input_parse(tr_opt)
ob_zbxapi: CZbx = CZbx(tr_opt["zbx_host"])
ob_zbxapi.login(tr_opt['zbx_login'], tr_opt['zbx_password'])
_zbx_map_create(ob_graph, ob_zbxapi)
