# インストール

ローカルのパスの通ってる所にでも置いてください。
依存としてpyvmomiを使用するので、pipでインストールしておいてください。

# 使い方

1. まず最初に、ESXiのホスト情報を作成する為に以下を実行します。

    ./mackerel_host_register.py -a ESXiに付けたホスト名 -s ESXiサーバにログインする為のDNSで解決できるホスト名 -u ESXi上のユーザ名 -p ユーザのログインパスワード
1. 出力されたJSONをmackerelに投げます。

    curl -X POST -H 'X-Api-Key: mackerelのAPIキー' -H 'Content-Type: application/json' https://mackerel.io/api/v0/hosts -d '{"roleFullnames": ["ロール名"], "meta": {"kernel": {"name": "VMware ESXi", "pratform_version": "6.0", "version": "6.5.0", "pratform_name": "VMware ESX Server", "release": "4887370", "os": "vmnix-x86"}, "agent-virsion": "1.0", "block_device": {}, "filesystem": {}, "agent-revision": "", "memory": {"total": "134121756kB", "free": "130743580kB"}, "cpu": [{"cores": 12, "physical_id": 0, "vendor_id": "intel", "mhz": 2200.0, "model_name": "Intel(R) Xeon(R) CPU E5-2650 v4 @ 2.20GHz"}, {"cores": 12, "physical_id": 1, "vendor_id": "intel", "mhz": 2200.0, "model_name": "Intel(R) Xeon(R) CPU E5-2650 v4 @ 2.20GHz"}], "agent-name": "PythonScript"}, "name": "esx-dev-06"}'

※ ロール名はちゃんと付けましょう
   コード直書きで横着してるけどそこは運用でカバー

1. mackerelにホスト情報を投げるとmackerel上のホストIDが返却されるのでメモしておきます。

1. send_mackerel_host_metric.shに今回のホスト情報行を追加します。

    eval ${CMD} "'$(./sv_res.py -i メモしたmackerel上のホストID -a ESXiに付けたホスト名 -s ESXiサーバにログインする為のDNSで解決できるホスト名 -u ESXi上のユーザ名 -p ユーザのログインパスワード)'" &

※ 最後に '&' を付けてバックグラウンド実行にしないと、複数サーバを登録した時に時間が掛り過ぎてしまうので注意する事

1. 変更したsend_mackerel_host_metric.shをcronで毎分実行に設定して様子をみます。
