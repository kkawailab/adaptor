#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import csv
import random
import pandas as pd
import os
import tempfile
from pathlib import Path
from flask import Flask, request
sys.path.append('../python/')

import e_Stat_API_Adaptor

app = Flask(__name__)
eStatAPI = e_Stat_API_Adaptor.e_Stat_API_Adaptor({
    # 取得したappId
    'appId': '#appID#',
    # データをダウンロード時に一度に取得するデータ件数
    'limit': '10000',
    # next_keyに対応するか否か(非対応の場合は上記のlimitで設定した件数のみしかダウンロードされない)
    # 対応時はTrue/非対応時はFalse
    'next_key': False,
    # 中間アプリの設置ディレクトリ
    'directory': '#絶対パス# /foo/bar/',
    # APIのバージョン
    'ver': '2.0',
    # データを取得形式
    'format': 'json'
})


@app.route(eStatAPI.path['http-public'] + '<appId>/search/<q>.<ext>', methods=['GET'])
def _search_id(appId, q, ext):
    eStatAPI._['appId'] = appId
    return eStatAPI.response(eStatAPI.get_output(eStatAPI.search_id(q, eStatAPI.path['dictionary-index']), ext), ext)


@app.route(eStatAPI.path['http-public'] + '<appId>/<cmd>/<id>.<ext>', methods=['GET'])
def _get_data(appId, cmd, id, ext):
    eStatAPI._['appId'] = appId
    return eStatAPI.response(eStatAPI.get_output(eStatAPI.get_csv(cmd, id), ext), ext)


@app.route(eStatAPI.path['http-public'] + '<appId>/merge/<ids>/<group_by>.<ext>', methods=['GET'])
def _merge_data(appId, ids, group_by, ext):
    eStatAPI._['appId'] = appId
    aggregate = request.args.get('aggregate') if request.args.get('aggregate') is not None else ''
    data = eStatAPI.merge_data(ids, group_by, aggregate)

    # 一時ファイルの安全な処理
    try:
        # tempfileを使用して安全に一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False,
                                         dir=eStatAPI.path['tmp'], encoding='utf-8') as tmp_file:
            tmp_path = tmp_file.name
            data.to_csv(tmp_file, quoting=csv.QUOTE_NONNUMERIC, index=None)

        # CSVを読み込み
        with open(tmp_path, 'r', encoding='utf-8') as f:
            tmp_csv = f.read()

        # 一時ファイルを削除
        os.remove(tmp_path)

        return eStatAPI.response(eStatAPI.get_output(tmp_csv, ext), ext)
    except Exception as e:
        # エラー時もファイルをクリーンアップ
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
