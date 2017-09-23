import atexit
import configparser
import requests
import sys
import ssl
import re
import vsanmgmtObjects
import vsanapiutils
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from requests.packages.urllib3.exceptions import InsecureRequestWarning

__all__ = ['get_vcenter_health_status', 'vm_count', 'vm_memory_count',
           'vm_cpu_count', 'powered_on_vm_count', 'get_vm', 'get_vms', 'get_uptime', 'get_cluster',
           'get_datastore', 'get_networks', 'get_vcenter_build', 'get_first_cluster',
           'get_cluster_status', 'get_vsan_version']


# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

config = configparser.ConfigParser()
AuthConfig = configparser.ConfigParser()

def auth_vcenter_rest():
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    username = config.get("vcenterConfig", "user")
    password = config.get("vcenterConfig", "password")
    print('Authenticating to vCenter REST API, user: {}'.format(username))
    resp = requests.post('{}/rest/com/vmware/cis/session'.format(url),
                         auth=(username, password), verify=False)
    authfile = open("/srv/avss/appdata/etc/auth.ini", 'w')
    AuthConfig.add_section('auth')
    AuthConfig.set('auth', 'sid', resp.json()['value'])
    AuthConfig.write(authfile)
    authfile.close()
    if resp.status_code != 200:
        print('Error! API responded with: {}'.format(resp.status_code))
        return
    return resp.json()['value']


def get_rest_api_data(req_url):
    AuthConfig.read("/srv/avss/appdata/etc/auth.ini")
    try:
        sid = AuthConfig.get("auth", "sid")
        print("Existing SID found; using cached SID")
    except:
        print("No SID loaded; aquiring new")
        auth_vcenter_rest()
        AuthConfig.read("/srv/avss/appdata/etc/auth.ini")
        sid = AuthConfig.get("auth", "sid")
    print('Requesting Page: {}'.format(req_url))
    resp = requests.get(req_url, verify=False,
                        headers={'vmware-api-session-id': sid})
    if resp.status_code != 200:
        if resp.status_code == 401:
            print("401 received; clearing stale SID")
            AuthConfig.remove_option('auth', 'sid')
            AuthConfig.remove_section('auth')
        print('Error! API responded with: {}'.format(resp.status_code))
        auth_vcenter_rest()
        get_rest_api_data(req_url)
        return
    return resp


# Function to login to vSphere SOAP API
# returns ServiceInstance
def auth_vcenter_soap(url, username, password):
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    username = config.get("vcenterConfig", "user")
    password = config.get("vcenterConfig", "password")
    print('Authenticating to vCenter SOAP API, user: {}'.format(username))

    context = None

    if sys.version_info[:3] > (2, 7, 8):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    pattern = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
    parsed = re.search(pattern, url)
    host = parsed.group('host')

    si = SmartConnect(host=host,
                      user=username,
                      pwd=password,
                      port=443,
                      sslContext=context)

    atexit.register(Disconnect, si)

    return si


# Function to login to vSAN Mgmt API
# return vSAN Managed Objects
def auth_vsan_soap(si):
    context = None
    if sys.version_info[:3] > (2, 7, 8):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    vcMos = vsanapiutils.GetVsanVcMos(si._stub, context=context)
    return vcMos


def get_vcenter_health_status():
    print("Retreiving vCenter Server Appliance Health ...")
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    health = get_rest_api_data('{}/rest/appliance/health/system'.format(url))
    j = health.json()
    return '{}'.format(j['value'])


def vm_count():
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    countarry = []
    for i in get_rest_api_data('{}/rest/vcenter/vm'.format(url)).json()['value']:
        countarry.append(i['name'])
    p = len(countarry)
    return p


def vm_memory_count():
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    memcount = []
    for i in get_rest_api_data('{}/rest/vcenter/vm'.format(url)).json()['value']:
        memcount.append(i['memory_size_MiB'])
    p = sum(memcount)
    return p


def vm_cpu_count():
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    cpucount = []
    for vm in get_rest_api_data('{}/rest/vcenter/vm'.format(url)).json()['value']:
        cpucount.append(vm['cpu_count'])
    sumvm = sum(cpucount)
    print(sumvm)
    return sumvm


def powered_on_vm_count():
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    onCount = []
    for i in get_rest_api_data('{}/rest/vcenter/vm'.format(url)).json()['value']:
        if i['power_state'] == 'POWERED_ON':
            onCount.append(i['name'])
    p = len(onCount)
    print(p)
    return p


def get_vm(name):
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    i = get_rest_api_data('{}/rest/vcenter/vm?filter.names={}'.format(url, name))
    return i.json()['value']

def get_vms():
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    i = get_rest_api_data('{}/rest/vcenter/vm'.format(url))
    return i.json()['value']


def get_uptime():
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    resp = get_rest_api_data('{}/rest/appliance/system/uptime'.format(url))
    k = resp.json()
    timeSeconds = k['value']/60/60
    return int(timeSeconds)

def get_cluster():
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    resp = get_rest_api_data('{}/rest/vcenter/host'.format(url))
    k = resp.json()
    hosts = []
    for i in k['value']:
        hosts.append(i['name'])
    return hosts


def get_datastore():
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    resp3 = get_rest_api_data('{}/rest/vcenter/datastore'.format(url))
    dsresp = resp3.json()
    datastores = []
    for i in dsresp['value']:
        datastores.append(i['free_space'])
    return datastores

def get_networks():
    config.read("/srv/avss/appdata/etc/config.ini")
    url = config.get("vcenterConfig", "url")
    resp = get_rest_api_data('{}/rest/vcenter/network'.format(url))
    k = resp.json()
    return k['value']

# Example of using vSphere SOAP API
def get_vcenter_build():
    config.read("etc/config.ini")
    url = config.get("vcenterConfig", "url")
    username = config.get("vcenterConfig", "user")
    password = config.get("vcenterConfig", "password")
    print("Retrieving vCenter Server Version and Build information ...")
    si = auth_vcenter_soap(url, username, password)
    return (si.content.about.apiVersion, si.content.about.build)


# Example of using vSphere SOAP API
# Not in use until we Alexa Skill can accept input
def getClusterInstance(clusterName, serviceInstance):
    content = serviceInstance.RetrieveContent()
    searchIndex = content.searchIndex
    datacenters = content.rootFolder.childEntity
    for datacenter in datacenters:
        cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
        if cluster is not None:
            return cluster
    return None


# Example of using vSphere SOAP API
def get_first_cluster(si):
    content = si.RetrieveContent()
    viewManager = content.viewManager
    container = viewManager.CreateContainerView(content.rootFolder,
                                                [vim.ClusterComputeResource],
                                                True)

    for c in container.view:
        cluster_view = c
        break

    container.Destroy()

    return cluster_view


# Example of using vSAN Mgmt API
def get_cluster_status():
    print("Retrieving vSphere Cluster Status ...")
    si = auth_vcenter_soap()
    vcMos = auth_vsan_soap(si)

    cluster = get_first_cluster(si)
    vccs = vcMos['vsan-cluster-config-system']
    vsanCluster = vccs.VsanClusterGetConfig(cluster=cluster)
    vsanEnabled = vsanCluster.enabled
    drsEnabled = cluster.configuration.drsConfig.enabled
    haEnabled = cluster.configuration.dasConfig.enabled
    return (drsEnabled, haEnabled, vsanEnabled)


# Example of using vSAN Mgmt API
def get_vsan_version():
    print("Retrieving vSAN Cluster Status ...")
    si = auth_vcenter_soap()
    vcMos = auth_vsan_soap(si)
    cluster = get_first_cluster(si)
    vchs = vcMos['vsan-cluster-health-system']
    results = vchs.VsanVcClusterQueryVerifyHealthSystemVersions(cluster)
    return results.vcVersion
