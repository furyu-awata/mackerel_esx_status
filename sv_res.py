#! /usr/bin/python3
# vim: set ts=4 sw=4 sts=0 fileencoding=utf-8 ff=unix :

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit
import datetime
import argparse
import json

# グローバル変数
host_id = ""
epoch_time = int(datetime.datetime.now().strftime("%s"))

# 引数処理
def get_args():
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')

    parser.add_argument('-i', '--hostid',
                        required=True,
                        action='store',
                        help='vSpehre service to connect host alias')

    parser.add_argument('-a', '--alias',
                        required=True,
                        action='store',
                        help='vSpehre service to connect host alias')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSpehre service to connect to')

    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use')

    parser.add_argument('-p', '--password',
                        required=True,
                        action='store',
                        help='Password to use')

    args = parser.parse_args()
    return args

# 結果出力用項目dict生成
def makeDictValue(name, value):
    result_dict = {}
    result_dict["hostId"] = host_id
    result_dict["time"] = epoch_time
    result_dict["name"] = name
    result_dict["value"] = value
    return result_dict

# CPU使用率の取得
def getCpuUsage(computeResourceView, hostResourceView):
    # CPUの合計周波数
    # 単体で取るなら掛け算が必要
    #total_cpu = hostResourceView.summary.hardware.cpuMhz * hostResourceView.summary.hardware.numCpuCores
    total_cpu = computeResourceView.summary.totalCpu
    # CPUの使用中周波数
    usage_cpu = hostResourceView.summary.quickStats.overallCpuUsage
    return float(usage_cpu) / float(total_cpu) * 100.0

# メモリ使用率の取得
def getMemoryUsage(computeResourceView, hostResourceView):
    # トータルメモリ(byteで帰ってくるのでMBに変換)
    # hostResourceViewからも取得できるが、CPUに併せてcomputeResourceViewから取得
    #total_mem = hostResourceView.summary.hardware.memorySize / 1024 / 1024
    total_mem = computeResourceView.summary.totalMemory / 1024 / 1024
    # メモリ使用量取得 (MBで取得)
    usage_mem = hostResourceView.summary.quickStats.overallMemoryUsage
    return float(usage_mem) / float(total_mem) * 100.0

# ネットワーク使用量を取得
def getNetworkValue(dnshost, perfManager, counter_name, instance):
    output=[]
    perf_dict = {}

    #perfManager = content.perfManager
    perfList = perfManager.perfCounter
    #build the vcenter counters for the objects
    for counter in perfList:
        counter_full = "{}.{}.{}".format(counter.groupInfo.key,counter.nameInfo.key,counter.rollupType)
        perf_dict[counter_full] = counter.key

    counterId = perf_dict[counter_name]
    metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance=instance)

    #startTime = datetime.datetime.now() - datetime.timedelta(hours=1)
    startTime = datetime.datetime.now() - datetime.timedelta(minutes=1)
    endTime = datetime.datetime.now()
    query = vim.PerformanceManager.QuerySpec(entity=dnshost,
                                             metricId=[metricId],
                                             intervalId=20,
                                             startTime=startTime,
                                             endTime=endTime)
    stats=perfManager.QueryPerf(querySpec=[query])
    # 最大値を返却する(kBpsなのでBpsにする為に1024倍)
    return max(stats[0].value[0].value) * 1024

# データストア使用率の取得
# データストアリストビューからも参照できるが、今回はホストリソースから取得
#ds_list = content.viewManager.CreateContainerView(content.rootFolder,
#                                                  [vim.Datastore],
#                                                  True)
#for ds in ds_list.view:
# …
# の様な感じ
def getDatastoreUsage(hostResourceView):
    result = {}
    for ds in hostResourceView.datastore:
        # 空き容量
        #print(ds.summary.freeSpace)
        # サイズ
        #print(ds.summary.capacity)
        # DataStore名
        if ds.summary.accessible:
            rate_datastore = (
                float(ds.summary.capacity) - 
                float(ds.summary.freeSpace)
                ) / float(ds.summary.capacity) * 100
            #print(ds.summary.name)
            #print(rate_datastore)
            # データストア毎の使用率を配列に格納
            result[ds.summary.name] = rate_datastore
    return result

# 仮想ホストの登録数取得
def getVmAllCount(virtualMachineView):
    return len(virtualMachineView)

# 稼動中の仮想ホスト数取得
def getVmRunningCount(virtualMachineView):
    vm_run_count = 0
    for vm in virtualMachineView:
        if vm.guest.guestState == "running":
            vm_run_count +=1
    return vm_run_count

# vSwitchと関連している物理NICの対応を取得
def getVSwitch(hostResourceView):
    result = {}
    for vswitch in hostResourceView.config.network.vswitch:
        pnics = []
        for pnic in vswitch.spec.bridge.nicDevice:
            pnics.append(pnic)
        result[vswitch.name] = pnics
    return result

# 物理NICの設定速度取得
def getNicSpeed(hostResourceView):
    result = {}
    for pnic in hostResourceView.configManager.networkSystem.networkInfo.pnic:
        if pnic.linkSpeed:
            result[pnic.device] = pnic.linkSpeed.speedMb
    return result

def main():
    # 引数処理
    args = get_args()

    global host_id
    host_id = args.hostid

    # Mackerelに送信するためのjsonオブジェクト
    result_json = []

    # SSL証明書対策
    context = None
    if hasattr(ssl, '_create_unverified_context'):
        context = ssl._create_unverified_context()

    # vCenterへ接続
    si = SmartConnect(host = args.host,
                      user = args.user,
                      pwd = args.password,
                      sslContext = context)

    # 処理完了時にvCenterから切断
    atexit.register(Disconnect, si)

    # コンテンツルートを取得
    #content = si.content
    content = si.RetrieveContent()

    # VirtualMachineを取得
    vm_list = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.VirtualMachine],
                                                      True)

    # HostSystemを取得
    host_list = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.HostSystem],
                                                      True)

    # ComputeResource
    rp_list = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.ComputeResource],
                                                      True)

    # VM情報の取得
    #print("------------ Virtual HOST ------------")
    # 設定されているVM数
    all_vm_count = getVmAllCount(vm_list.view)
    #print(all_vm_count)
    # 起動しているVM数
    vm_run_count = getVmRunningCount(vm_list.view)
    #print(vm_run_count)
    result_json.append(makeDictValue("vm.count.all", all_vm_count))
    result_json.append(makeDictValue("vm.count.running", vm_run_count))

    # CPU
    rate_cpu = getCpuUsage(rp_list.view[0], host_list.view[0])
    #print("------------ CPU Usage ------------")
    #print(round(rate_cpu, 2))
    result_json.append(makeDictValue("cpu.usage.all", round(rate_cpu, 2)))

    # Memory
    rate_mem = getMemoryUsage(rp_list.view[0], host_list.view[0])
    #print("------------ Mem Usage ------------")
    #print(round(rate_mem, 2))
    result_json.append(makeDictValue("memory.usage.all", round(rate_mem, 2)))

    # datastore
    #print("------------ DataStore ------------")
    rate_datastores = getDatastoreUsage(host_list.view[0])
    for datastore in rate_datastores.keys():
        #print(datastore + "	" + str(round(rate_datastores[datastore], 2)))
        result_json.append(makeDictValue("datastore.usage." + datastore, round(rate_datastores[datastore], 2)))

    # Network

    # vSwich毎に纏めようかと思ったが、結局未使用
    #print("------------ vSwitch ------------")
    #vswitch = getVSwitch(host_list.view[0])
    #print(vswitch)

    #print("------------ NIC & Speed ------------")
    pnics = getNicSpeed(host_list.view[0])
    #print(pnic)

    #print("------------ NIC Rx Tx Bytes ------------")
    dnshost = content.searchIndex.FindByDnsName(dnsName=args.host, vmSearch=False)
    if  dnshost == None:
        dnshost = content.searchIndex.FindByDnsName(dnsName=args.alias, vmSearch=False)

    interfaces = [""]
    interfaces.extend(pnics.keys())
    #for counter_name in ["bytesRx", "bytesTx"]:
    for counter_name in ["received", "transmitted"]:
        for instance in interfaces:
            try:
                read_kbyte = getNetworkValue(dnshost=dnshost,
                                             perfManager=content.perfManager,
                                             counter_name="net." + counter_name + ".average",
                                             instance=instance)
                if instance == "":
                    instance = "total"
                result_json.append(makeDictValue("network." + counter_name + "." + instance, read_kbyte))
                #print("{}	{}	{}".format(counter_name, instance, read_kbyte))
            except:
                pass

    print(json.dumps(result_json))
    return(0)

# ここからはじまる
if __name__ == '__main__':
    main()
