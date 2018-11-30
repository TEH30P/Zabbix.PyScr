import os as m_os
import pyzabbix as m_zbx
import json as m_json
import re as m_re

#######################################

dct_opt: dict = {}
str_opt_path: str = m_os.path.splitext(m_os.path.realpath(__file__))[0] + '.json'

with open(str_opt_path, 'r+t') as rd_js:
    dct_opt = m_json.load(rd_js)

#######################################


def cdp_icon_get(i_cdp: str) -> str:
    for tpl_kv in dict(dct_opt['node_icon_off']).items():
        if m_re.fullmatch(tpl_kv[0], i_cdp) is not None:
            return str(tpl_kv[1])

    return str(dct_opt['node_icon_def'])


obj_zbx = m_zbx.ZabbixAPI(dct_opt["zbx_host"])
obj_zbx.login(dct_opt['zbx_login'], dct_opt['zbx_password'])

str_groupid_l = []

for str_name in dct_opt["host_group_l"]:
    for obj_hg in obj_zbx.hostgroup.get(output=["name"], search={"name": str_name}):
        if obj_hg["name"] == str_name:
            str_groupid_l += [obj_hg["groupid"]]

dct_hid: dict = {}
dct_hname: dict = {}
str_hunk_s: set = set()
tpl_hcnn_s: set = set()
dct_hcnn_d: dict = dict()

for dct_h in obj_zbx.host.get(output=['name', 'host'], groupids=str_groupid_l):
    zbx_item_get_para: dict = dct_opt['cdp_item_filt'].copy()
    zbx_item_get_para['hostids'] = [dct_h['hostid']]

    str_cdp_nei_l: list = []
    num_cdp_locif_oid_l: list = []
    str_cdp: str = ''

    for dct_i in obj_zbx.item.get(**zbx_item_get_para):  # output=['name', 'key_', 'state', 'status' 'lastclock', 'lastvalue'],:
        if int(dct_i['type']) == 4 and int(dct_i['state']) == 0 and int(dct_i['status']) == 0:
            str_iv: str = dct_i['lastvalue']
        else:
            continue

        str_i_snmp_oid: str = str(dct_i['snmp_oid'])

        if str_i_snmp_oid == '1.3.6.1.4.1.9.9.23.1.3.4.0':
            str_cdp = str_iv
            dct_hid[str_cdp] = 'id' + dct_h['hostid']
            dct_hname[str_cdp] = dct_h['name']
            str_hunk_s.discard(str_cdp)
        elif str_i_snmp_oid.startswith('1.3.6.1.4.1.9.9.23.1.2.1.1.6.'):
            str_cdp_nei_l.append(str_iv)
            num_cdp_locif_oid = int(str_i_snmp_oid.split('.')[14])
            num_cdp_locif_oid_l.append(num_cdp_locif_oid)

            if str_iv not in dct_hid:
                str_hunk_s.add(str_iv)

    tpl_hcnn_s |= set([(str_cdp, str_cdp_nei) for str_cdp_nei in str_cdp_nei_l])
    dct_edge_filt_l: list = []

    for num_cdp_locif_oid in num_cdp_locif_oid_l:
        dct_edge_filt: dict = dct_opt['edge_trigger'].copy()
        dct_edge_filt['description'] = [str_it.replace('{#LOCAL_IF_OID}', str(num_cdp_locif_oid)) for str_it in list(dct_edge_filt['description'])]
        dct_edge_filt['item'] = [str_it.replace('{#LOCAL_IF_OID}', str(num_cdp_locif_oid)) for str_it in list(dct_edge_filt['item'])]

        dct_edge_filt_l.append(dct_edge_filt)

    for str_cdp_nei in str_cdp_nei_l:
        if (str_cdp_nei in dct_hcnn_d) or (str_cdp_nei in dct_hid):
            continue

        dct_hcnn_d[str_cdp_nei] = {'map_icon_off': cdp_icon_get(str_cdp_nei), 'map_edge': dict()}

    if str_cdp not in dct_hcnn_d:
        dct_hcnn_d[str_cdp] = \
            {   'map_icon_off': cdp_icon_get(str_cdp)
            ,   'map_edge': dict(zip(str_cdp_nei_l, dct_edge_filt_l))}
    else:
        tpl_hcnn = dct_hcnn_d[str_cdp]
        tpl_hcnn['map_edge'] = dict(zip(str_cdp_nei_l, dct_edge_filt_l))

num: int = 0

for hunk in str_hunk_s:
    dct_hid[hunk] = 'unk{0}'.format(num)
    num += 1

dct_hcnn_d = dict([(dct_hid[tpl_kv[0]], tpl_kv[1]) for tpl_kv in dct_hcnn_d.items()])

for str_key_it in dct_hcnn_d.keys():
    dct_hcnn_edge = dct_hcnn_d[str_key_it]['map_edge']
    dct_hcnn_d[str_key_it]['map_edge'] = dict([(dct_hid[tpl_kv[0]], tpl_kv[1]) for tpl_kv in dct_hcnn_edge.items()])

tpl_hcnnu_s = set([(tpl_hcnn[1], tpl_hcnn[0]) for tpl_hcnn in tpl_hcnn_s])

for tpl_hcnn in tpl_hcnn_s:
    if tpl_hcnn in tpl_hcnnu_s:
        tpl_hcnnu_s.discard((tpl_hcnn[1], tpl_hcnn[0]))

# print(tpl_hcnn_s)
# print(tpl_hcnnu_s)
# print(hid_d)

with open(dct_opt['file_dot_path'], 'w+t') as wr_dot:
    wr_dot.write('graph Zbx {\n')
    wr_dot.write('    overlap=false; sep="+0";\n')
    wr_dot.write('    edge [splines=polyline];\n')

    wr_dot.write('\n')

    for tpl_hid_kv in dct_hid.items():
        if tpl_hid_kv[0] in dct_hname:
            wr_dot.write('    {0} [label="{1}", shape=ellipse, height=1.25, width=1];\n'.format(tpl_hid_kv[1], dct_hname[tpl_hid_kv[0]]))
        else:
            wr_dot.write('    {0} [label="{1}", shape=ellipse, height=1.25, width=1];\n'.format(tpl_hid_kv[1], tpl_hid_kv[0]))

    wr_dot.write('\n')

    for tpl_hcnn in tpl_hcnnu_s:
        wr_dot.write('    {0} -- {1};\n'.format(dct_hid[tpl_hcnn[0]], dct_hid[tpl_hcnn[1]]))
        num += 1

    wr_dot.write('}')

with open(dct_opt['file_json_path'], 'w+t') as wr_js:
    m_json.dump(dct_hcnn_d, wr_js)