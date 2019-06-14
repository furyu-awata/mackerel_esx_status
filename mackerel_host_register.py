#! /usr/bin/python3
# vim: set ts=4 sw=4 sts=0 fileencoding=utf-8 ff=unix :

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit
import datetime
import argparse
import json

# 引数処理
def get_args():
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')

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

def getKernel(host_view):
    result_json = {}
    result_json["name"]             = host_view.config.product.name
    result_json["os"]               = host_view.config.product.osType
    result_json["pratform_name"]    = host_view.config.product.licenseProductName
    result_json["pratform_version"] = host_view.config.product.licenseProductVersion
    result_json["release"]          = host_view.config.product.build
    result_json["version"]          = host_view.config.product.version

    return result_json

def getCpu(host_view):
    result_json = []
    for info in host_view.hardware.cpuPkg:
        cpu_json = {}
        cpu_json["model_name"]  = info.description
        cpu_json["mhz"]         = round(float(info.hz) / 1000000.0, 2)
        cpu_json["physical_id"] = info.index
        cpu_json["cores"]       = host_view.hardware.cpuInfo.numCpuCores / host_view.hardware.cpuInfo.numCpuPackages
        cpu_json["vendor_id"]   = info.vendor

        result_json.append(cpu_json)

    return result_json

def getMemory(host_view):
    result_json = {}
    result_json["total"] = str(host_view.summary.hardware.memorySize / 1024) + "kB"
    result_json["free"]  = str(host_view.summary.hardware.memorySize /1024 - 
                               host_view.summary.quickStats.overallMemoryUsage * 1024) + "kB"
    return result_json

def main():
    # 引数処理
    args = get_args()

    # Mackerelに送信するためのjsonオブジェクト
    result_json = {}

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

    # HostSystemを取得
    host_list = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.HostSystem],
                                                      True)

    # 送信情報設定
    # ホスト名
    result_json["name"] = args.alias
    # ロール
    result_json["roleFullnames"] = ["TEST:ESXi"]
    # meta情報
    result_json["meta"] = {}
    result_json["meta"]["agent-name"] = "PythonScript"
    result_json["meta"]["agent-revision"] = ""
    result_json["meta"]["agent-virsion"] = "1.0"
    # meta情報 kernel
    result_json["meta"]["kernel"] = getKernel(host_list.view[0])
    # meta情報 cpu
    result_json["meta"]["cpu"] = getCpu(host_list.view[0])
    # meta情報 memory
    result_json["meta"]["memory"] = getMemory(host_list.view[0])
    # block_deviceとfilesystemは不明なので空にしておく
    result_json["meta"]["block_device"] = {}
    result_json["meta"]["filesystem"] = {}

    print(json.dumps(result_json))
    return(0)

# ここからはじまる
if __name__ == '__main__':
    main()
