#!/bin/bash
# vim: set ts=4 sw=4 sts=0 fileencoding=utf-8 ff=unix :

# コマンド実行ディレクトリ
CWD=$(cd $(dirname $0); pwd)
# カレントディレクトリを移動しておく
cd $CWD

# Mackerelに送出する為のcurlコマンド
CMD="curl -X POST -H 'X-Api-Key: mackerelのキー' -H 'Content-Type: application/json' https://mackerel.io/api/v0/tsdb -d"

eval ${CMD} "'$(./sv_res.py -i IDだよ -a ホスト名ね -s 完全修飾ホスト名を -u ユーザ名 -p パスワード)'" &

wait

