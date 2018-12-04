import os as m_os
import json as m_json
import re as m_re

from pyzabbix import ZabbixAPI as CZbx

#######################################

tx_optpath: str = m_os.path.splitext(m_os.path.realpath(__file__))[0] + '.json'

with open(tx_optpath, 'r+t') as rd_js:
    tr_opt: dict = m_json.load(rd_js)

#######################################


def _cdp_icon_get(i_cdp: str) -> str:
    for tp_kv in dict(tr_opt['node_icon_off']).items():
        if m_re.fullmatch(tp_kv[0], i_cdp, m_re.IGNORECASE) is not None:
            return str(tp_kv[1])

    return str(tr_opt['node_icon_def'])


ob_zbx = CZbx(tr_opt["zbx_host"])
ob_zbx.login(tr_opt['zbx_login'], tr_opt['zbx_password'])

tx_zbxgroupid_cl: list = []

for tx_name in tr_opt["host_group_l"]:
    for kv_zbxgroup in ob_zbx.hostgroup.get(output=['name'], search={'name': tx_name}):
        if kv_zbxgroup['name'] == tx_name:
            tx_zbxgroupid_cl += [kv_zbxgroup['groupid']]

tx_cdp_to_mapnode_kv: dict = {}
tx_cdp_to_zbxhostname_kv: dict = {}
tx_cdp_zbxunknown_st: set = set()
tp_cdp_pair_st: set = set()
tr_jsonres: dict = {}

for kv_zbxhost in ob_zbx.host.get(output=['name', 'host'], groupids=tx_zbxgroupid_cl):
    kv_zbx_item_get_arg: dict = tr_opt['cdp_item_filt'].copy()
    kv_zbx_item_get_arg['hostids'] = [kv_zbxhost['hostid']]

    tx_cdp_neighbour_cl: list = []
    nm_snmpoid_localif_cl: list = []
    tx_cdp: str = ''

    for kv_zbxitem in ob_zbx.item.get(**kv_zbx_item_get_arg):
        if int(kv_zbxitem['type']) == 4 and int(kv_zbxitem['state']) == 0 and int(kv_zbxitem['status']) == 0:
            tx_zbxitem_lastval: str = kv_zbxitem['lastvalue']
        else:
            continue

        tx_zbxitem_snmpoid: str = str(kv_zbxitem['snmp_oid'])

        if tx_zbxitem_snmpoid == '1.3.6.1.4.1.9.9.23.1.3.4.0':
            tx_cdp = tx_zbxitem_lastval
            tx_cdp_to_mapnode_kv[tx_cdp] = 'id' + kv_zbxhost['hostid']
            tx_cdp_to_zbxhostname_kv[tx_cdp] = kv_zbxhost['name']
            tx_cdp_zbxunknown_st.discard(tx_cdp)
        elif tx_zbxitem_snmpoid.startswith('1.3.6.1.4.1.9.9.23.1.2.1.1.6.'):
            tx_cdp_neighbour_cl.append(tx_zbxitem_lastval)
            nm_snmpoid_localif = int(tx_zbxitem_snmpoid.split('.')[14])
            nm_snmpoid_localif_cl.append(nm_snmpoid_localif)

            if tx_zbxitem_lastval not in tx_cdp_to_mapnode_kv:
                tx_cdp_zbxunknown_st.add(tx_zbxitem_lastval)

    tp_cdp_pair_st |= set([(tx_cdp, tx_cdp_nei) for tx_cdp_nei in tx_cdp_neighbour_cl])
    kv_jsonres_mapedge_filt_cl: list = []

    for nm_snmpoid_localif in nm_snmpoid_localif_cl:
        kv_edge_filt: dict = tr_opt['edge_trigger'].copy()
        kv_edge_filt['description'] \
            = [tx_it.replace('{#LOCAL_IF_OID}', str(nm_snmpoid_localif)) for tx_it in list(kv_edge_filt['description'])]
        kv_edge_filt['item'] \
            = [tx_it.replace('{#LOCAL_IF_OID}', str(nm_snmpoid_localif)) for tx_it in list(kv_edge_filt['item'])]

        kv_jsonres_mapedge_filt_cl.append(kv_edge_filt)

    for tx_cdp_neighbour in tx_cdp_neighbour_cl:
        if (tx_cdp_neighbour in tr_jsonres) or (tx_cdp_neighbour in tx_cdp_to_mapnode_kv):
            continue

        tr_jsonres[tx_cdp_neighbour] = {'map_icon_off': _cdp_icon_get(tx_cdp_neighbour), 'map_edge': dict()}

    if tx_cdp not in tr_jsonres:
        tr_jsonres[tx_cdp] = \
            {   'map_icon_off': _cdp_icon_get(tx_cdp)
            ,   'map_edge': dict(zip(tx_cdp_neighbour_cl, kv_jsonres_mapedge_filt_cl))}
    else:
        tr_jsonres[tx_cdp]['map_edge'] = dict(zip(tx_cdp_neighbour_cl, kv_jsonres_mapedge_filt_cl))

nm: int = 0

for tx_it in tx_cdp_zbxunknown_st:
    tx_cdp_to_mapnode_kv[tx_it] = f'unk{nm}'
    nm += 1

# Replacing cdpGlobalDeviceId with the corresponding "dot" node names. And saving the result to "json" file.

tr_jsonres = dict([(tx_cdp_to_mapnode_kv[tp_kv[0]], tp_kv[1]) for tp_kv in tr_jsonres.items()])

for tx_it in tr_jsonres.keys():
    tr_jsonres_edge = tr_jsonres[tx_it]['map_edge']
    tr_jsonres[tx_it]['map_edge'] \
        = dict([(tx_cdp_to_mapnode_kv[tp_kv[0]], tp_kv[1]) for tp_kv in tr_jsonres_edge.items()])

with open(tr_opt['file_json_path'], 'w+t') as wr_js:
    m_json.dump(tr_jsonres, wr_js)

# Creating truly unique cdppair set.

tp_cdppair_uniq_st = set([(tp_hcnn[1], tp_hcnn[0]) for tp_hcnn in tp_cdp_pair_st])

for tp_cdppair in tp_cdp_pair_st:
    if tp_cdppair in tp_cdppair_uniq_st:
        tp_cdppair_uniq_st.discard((tp_cdppair[1], tp_cdppair[0]))

# Generating "dot" file.

with open(tr_opt['file_dot_path'], 'w+t') as wr_dot:
    wr_dot.write('graph Zbx {\n')
    wr_dot.write('    overlap=false; sep="+0";\n')
    wr_dot.write('    edge [splines=polyline];\n')

    wr_dot.write('\n')

    for tp_it in tx_cdp_to_mapnode_kv.items():
        if tp_it[0] in tx_cdp_to_zbxhostname_kv:
            wr_dot.write(
                f'    {tp_it[1]} [label="{tx_cdp_to_zbxhostname_kv[tp_it[0]]}", shape=ellipse, height=1.25, width=1];\n')
        else:
            wr_dot.write(f'    {tp_it[1]} [label="{tp_it[0]}", shape=ellipse, height=1.25, width=1];\n')

    wr_dot.write('\n')

    for tp_cdppair in tp_cdppair_uniq_st:
        wr_dot.write(f'    {tx_cdp_to_mapnode_kv[tp_cdppair[0]]} -- {tx_cdp_to_mapnode_kv[tp_cdppair[1]]};\n')

    wr_dot.write('}')
