#!/usr/bin/env python
# -*- coding: utf-8 -*-

# # # # # # # # # # # # # # # # # # # # # # # #
#
#  e-Stat API Adaptor
#  (c) 2016 National Statistics Center
#  License: MIT
#
# # # # # # # # # # # # # # # # # # # # # # # #

import os
import subprocess
import unicodedata
import requests
import json
import csv
import re
import io
import random
import numpy
import math
import pandas as pd
import logging
from pathlib import Path
from flask import request
from flask import Response
from flask import Flask

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class e_Stat_API_Adaptor:

    def __init__(self, _):
        # アプリ設定
        self._ = _
        # パス設定
        self.path = {
            # データダウンロード時に使用するディレクトリ
            'tmp': self._['directory'] + 'tmp/',
            # CSVのディレクトリ
            'csv': self._['directory'] + 'data-cache/',
            # 全ての統計IDを含むJSONファイルのパス
            'statid-json': self._['directory'] + 'dictionary/all.json.dic',
            # indexを作成するパス
            'dictionary-index': self._['directory'] + 'dictionary/index.list.dic',
            # ユーザーindex
            'dictionary-user': self._['directory'] + 'dictionary/user.csv.dic',
            # 統計センターindex
            'dictionary-stat-center': self._['directory'] + 'dictionary/stat.center.csv.dic',
            # 統計センターindexのダウンロード用URL
            'url-dictionary-stat-center': 'http://www.e-stat.go.jp/api/sample2/api-m/stat-center-index.csv',
            # 詳細(n-gram形式)
            'dictionary-detail': self._['directory'] + 'dictionary/detail/',
            # 公開ディレクトリ
            'http-public': '/'
        }
        self.msg = {
            'check-extension': 'Oops! check your extension!',
            'invalid-id': 'Invalid statistics data ID',
            'invalid-query': 'Invalid query string',
            'api-error': 'API request failed'
        }
        self.url = {
            'host': 'http://api.e-stat.go.jp',
            'path': '/'.join([
                'rest', self._['ver'], 'app', 'json', 'getStatsData'
            ])
        }
        self.csv_header = {
            'index': ['statsDataId', '調査名', '調査年月', '組織名', 'カテゴリー'],
            'user': ['statsDataId', '検索語']
        }
        self.header = {'Access-Control-Allow-Origin': '*'}
        self.random_str = 'ABCDEFGHIJKLMNOPQRTSUVWXYZabcdefghijklmnopqrstuvwxyz1234567890'
        self.cache = {}
        # N-グラムの設定
        self.gram = 2

        # ディレクトリの作成
        self._ensure_directories()

    def _ensure_directories(self):
        """必要なディレクトリを作成"""
        directories = [
            self.path['tmp'],
            self.path['csv'],
            self._['directory'] + 'dictionary/',
            self.path['dictionary-detail']
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def _validate_stats_id(self, stats_id):
        """統計IDの検証"""
        if not stats_id or not isinstance(stats_id, str):
            raise ValueError(self.msg['invalid-id'])
        # 統計IDは数字のみ
        if not re.match(r'^\d+$', stats_id):
            raise ValueError(self.msg['invalid-id'])
        return True

    def _validate_query(self, query):
        """検索クエリの検証"""
        if not query or not isinstance(query, str):
            raise ValueError(self.msg['invalid-query'])
        # 基本的なサニタイゼーション
        if re.search(r'[;&|`$\n\r]', query):
            raise ValueError(self.msg['invalid-query'])
        return True

    # 全ての統計IDをダウンロード
    def load_all_ids(self):
        try:
            load_uri = self.build_uri({
                'appId': self._['appId'],
                'searchWord': ''
            }).replace('getStatsData', 'getStatsList')

            logger.info(f"Downloading all statistics IDs from: {load_uri}")
            response = requests.get(load_uri, timeout=30)
            response.raise_for_status()

            with open(self.path['statid-json'], 'w', encoding='utf-8') as f:
                json.dump(response.json(), f, ensure_ascii=False, indent=2)

            logger.info(f"Successfully saved to: {self.path['statid-json']}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to download statistics IDs: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    # ダウンロードした統計表からインデックスファイルを作成する
    def build_statid_index(self):
        try:
            jd = self.load_json(
                self.path['statid-json'])['GET_STATS_LIST']['DATALIST_INF']['TABLE_INF']

            rows = []
            for j in jd:
                try:
                    row = '-'.join([
                        j['@id'],
                        j['STAT_NAME']['$'],
                        str(j['SURVEY_DATE']),
                        j['GOV_ORG']['$'],
                        j['MAIN_CATEGORY']['$'],
                        j['SUB_CATEGORY']['$']
                    ]) + '.dic'
                    rows.append(row)
                except KeyError as e:
                    logger.warning(f"Missing key in data: {e}")
                    continue

            with open(self.path['dictionary-index'], 'w', encoding='utf-8') as f:
                f.write('\n'.join(rows))

            logger.info(f"Index created: {len(rows)} entries")
            return True
        except Exception as e:
            logger.error(f"Failed to build index: {e}")
            raise

    # 統計センターが作成するindexのダウンロード用関数
    def load_stat_center_index(self):
        try:
            logger.info(f"Downloading stat center index from: {self.path['url-dictionary-stat-center']}")
            response = requests.get(self.path['url-dictionary-stat-center'], timeout=30)
            response.raise_for_status()

            with open(self.path['dictionary-stat-center'], 'wb') as f:
                f.write(response.content)

            logger.info("Stat center index downloaded successfully")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to download stat center index: {e}")
            raise

    def build_detailed_index(self):
        try:
            jd = self.load_json(
                self.path['statid-json'])['GET_STATS_LIST']['DATALIST_INF']['TABLE_INF']

            for i, j in enumerate(jd):
                filename = '-'.join([
                    j['@id'],
                    j['STAT_NAME']['$'],
                    str(j['SURVEY_DATE']),
                    j['GOV_ORG']['$'],
                    j['MAIN_CATEGORY']['$'],
                    j['SUB_CATEGORY']['$']
                ]) + '.dic'

                try:
                    STATISTICS_NAME = self.create_n_gram_str(
                        j['STATISTICS_NAME'], self.gram)
                except:
                    STATISTICS_NAME = ''
                try:
                    TITLE = self.create_n_gram_str(j['TITLE']['$'], self.gram)
                except:
                    TITLE = ''

                with open(self.path['dictionary-detail'] + filename, 'w', encoding='utf-8') as f:
                    f.write('\n'.join([STATISTICS_NAME, TITLE]))

            logger.info(f"Detailed index built: {len(jd)} entries")
            return True
        except Exception as e:
            logger.error(f"Failed to build detailed index: {e}")
            raise

    def create_n_gram_str(self, text, gram):
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r'[\s\(\)\-,\[\]]', '', text).replace('・', '')
        ngrams = [text[i:i+gram] for i in range(len(text)) if i+gram <= len(text)]
        return ','.join([ng for ng in ngrams if ng])

    def search_detailed_index(self, q):
        self._validate_query(q)
        detail_files = os.listdir(self.path['dictionary-detail'])
        detail_index = []

        for dic in detail_files:
            try:
                with open(self.path['dictionary-detail'] + dic, 'r', encoding='utf-8') as f:
                    for row in f.readlines():
                        if q in row:
                            detail_index.append(','.join([dic.split('-')[0], q]))
            except Exception as e:
                logger.warning(f"Error reading {dic}: {e}")
                continue

        return detail_index

    def create_user_index_from_detailed_index(self, q):
        try:
            results = self.search_detailed_index(q)
            with open(self.path['dictionary-user'], 'a', encoding='utf-8') as f:
                f.write('\n'.join(results) + '\n')
            logger.info(f"User index updated with {len(results)} entries")
            return True
        except Exception as e:
            logger.error(f"Failed to create user index: {e}")
            raise

    def build_uri(self, param):
        return '?'.join([
            '/'.join([self.url['host'], self.url['path']]),
            '&'.join([k + '=' + str(v) for k, v in param.items()])
        ])

    def load_json(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as json_data:
                return json.load(json_data)
        except FileNotFoundError:
            logger.error(f"File not found: {path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {path}: {e}")
            raise

    def search_id(self, q, _index, _header='index'):
        self._validate_query(q)

        try:
            with open(_index, 'r', encoding='utf-8') as f:
                content = f.read()

            if q == 'index':
                rows = [[c for c in line.split('-') if '.dic' not in c]
                       for line in content.split('\n') if line]
            else:
                lines = content.split('\n')
                rows = []
                for line_num, line in enumerate(lines, 1):
                    if q in line:
                        parts = [str(line_num)] + [c for c in line.split('-') if '.dic' not in c]
                        rows.append(parts)

            # 行の整形
            for i, r in enumerate(rows):
                if len(r) == 6:
                    rows[i][2] = rows[i][2] + '-' + rows[i][3]
                    del rows[i][3]
                rows[i] = ','.join(rows[i])

            result = '\n'.join([','.join(self.csv_header[_header]), '\n'.join(rows)])
            return result
        except FileNotFoundError:
            logger.error(f"Index file not found: {_index}")
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def get_all_data(self, statsDataId, next_key):
        self._validate_stats_id(statsDataId)

        self.cache['tmp'] = os.path.join(
            self.path['tmp'],
            '.'.join([self._['appId'], statsDataId, next_key, 'json'])
        )

        try:
            if not os.path.exists(self.cache['tmp']):
                apiURI = self.build_uri({
                    'appId': self._['appId'],
                    'statsDataId': statsDataId,
                    'limit': self._['limit'],
                    'startPosition': next_key
                })

                logger.info(f"Fetching data from API: {statsDataId}, position: {next_key}")
                response = requests.get(apiURI, timeout=60)
                response.raise_for_status()

                with open(self.cache['tmp'], 'w', encoding='utf-8') as f:
                    json.dump(response.json(), f, ensure_ascii=False, indent=2)

            data = self.load_json(self.cache['tmp'])
            RESULT_INF = data['GET_STATS_DATA']['STATISTICAL_DATA']['RESULT_INF']
            NEXT_KEY = '-1' if 'NEXT_KEY' not in RESULT_INF else RESULT_INF['NEXT_KEY']

            return str(NEXT_KEY)
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            # エラー時は一時ファイルを削除
            self._cleanup_temp_files(statsDataId)
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_all_data: {e}")
            self._cleanup_temp_files(statsDataId)
            return None

    def _cleanup_temp_files(self, statsDataId):
        """一時ファイルのクリーンアップ"""
        try:
            pattern = f"{self._['appId']}.{statsDataId}.*.json"
            temp_dir = Path(self.path['tmp'])
            for file in temp_dir.glob(pattern):
                file.unlink()
                logger.info(f"Cleaned up temp file: {file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")

    def convert_raw_json_to_csv(self, statsDataId):
        self._validate_stats_id(statsDataId)

        try:
            self.cache['csv'] = os.path.join(self.path['csv'], statsDataId + '.csv')
            dat = {'header': None, 'body': [], 'keys': None}

            # 一時JSONファイルの取得
            pattern = f"{self._['appId']}.{statsDataId}.*.json"
            temp_dir = Path(self.path['tmp'])
            json_files = sorted(temp_dir.glob(pattern),
                              key=lambda x: int(x.stem.split('.')[2]))

            if not json_files:
                raise FileNotFoundError(f"No JSON files found for {statsDataId}")

            logger.info(f"Converting {len(json_files)} JSON files to CSV")

            for i, json_file in enumerate(json_files):
                logger.info(f"Processing {i+1}/{len(json_files)}: {json_file.name}")
                jd = self.load_json(str(json_file))

                if i == 0:
                    dat['header'] = [
                        k.replace('@', '')
                        for k in jd['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE'][0].keys()
                    ]
                    dat['keys'] = jd['GET_STATS_DATA']['STATISTICAL_DATA']['CLASS_INF']

                dat['body'].extend(jd['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE'])

            # ヘッダーとボディの作成
            _h = {}
            _b = {}

            for o in dat['keys']['CLASS_OBJ']:
                o['CLASS'] = [o['CLASS']] if not isinstance(o['CLASS'], list) else o['CLASS']
                if o['@id'] not in _b:
                    _b[o['@id']] = {}
                for oc in o['CLASS']:
                    _b[o['@id']][oc['@code']] = oc['@name']
                _h[o['@id']] = o['@name']

            newCSV = [[_h.get(h, h) for h in dat['header']]]
            newCSV.append(dat['header'])

            for body in dat['body']:
                newCSV.append(list(body.values()))

            # データの変換
            for i, x in enumerate(newCSV):
                if i > 0:
                    for j, d in enumerate(x):
                        if dat['header'][j] in _b and d in _b[dat['header'][j]]:
                            newCSV[i][j] = _b[dat['header'][j]][d]
                        else:
                            newCSV[i][j] = d

            # CSV書き込み
            with open(self.cache['csv'], 'w', encoding='utf-8', newline='') as f:
                csv.writer(f, quoting=csv.QUOTE_NONNUMERIC).writerows(newCSV)

            logger.info(f"CSV created successfully: {self.cache['csv']}")

            # 一時ファイルの削除
            for json_file in json_files:
                json_file.unlink()

            return True
        except Exception as e:
            logger.error(f"Failed to convert JSON to CSV: {e}")
            self._cleanup_temp_files(statsDataId)
            raise

    def merge_data(self, statsDataId, group_by, aggregate):
        statsDataId_list = statsDataId.split(',')

        # IDの検証
        for sid in statsDataId_list:
            self._validate_stats_id(sid.strip())

        data = {}
        for sid in statsDataId_list:
            sid = sid.strip()
            csv_path = os.path.join(self.path['csv'], sid + '.csv')

            if not os.path.exists(csv_path):
                logger.info(f"Downloading data for {sid}")
                self.get_all_data(sid, '1')
                self.convert_raw_json_to_csv(sid)

            data[sid] = pd.read_csv(csv_path, skiprows=[0])
            data[sid]['stat-id'] = sid

        # データの結合
        for k, v in data.items():
            v.rename(columns=lambda x: x.replace('$', '$' + k), inplace=True)

        data = pd.concat([v for k, v in data.items()], ignore_index=True)

        if group_by != 'all':
            group_cols = group_by.split(',')

            # 集約処理
            if aggregate == 'sum':
                data = data.groupby(group_cols).sum()
            elif aggregate == 'min':
                data = data.groupby(group_cols).min()
            elif aggregate == 'max':
                data = data.groupby(group_cols).max()
            elif aggregate == 'median':
                data = data.groupby(group_cols).median()
            elif aggregate == 'count':
                data = data.groupby(group_cols).count()
            elif aggregate == 'var':
                data = data.groupby(group_cols).var()
            elif aggregate == 'std':
                data = data.groupby(group_cols).std()
            elif aggregate == 'mean':
                data = data.groupby(group_cols).mean()

            if aggregate:
                data = data.loc[:, [c for c in data.columns if '$' in c]]
            else:
                data = data.loc[:, [c for c in data.columns if '$' in c or group_by in c]]

        return data.reset_index()

    def remove_file(self, filepath):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Removed file: {filepath}")
            else:
                # グロブパターンの場合
                for file in Path().glob(filepath):
                    file.unlink()
                    logger.info(f"Removed file: {file}")
        except Exception as e:
            logger.error(f"Failed to remove file {filepath}: {e}")
            raise

    def get_csv(self, cmd, statsDataId):
        self._validate_stats_id(statsDataId)

        cmd_map = {'get': 'cat', 'head': 'head', 'tail': 'tail'}
        if cmd not in cmd_map:
            raise ValueError(f"Invalid command: {cmd}")

        csv_path = os.path.join(self.path['csv'], statsDataId + '.csv')

        if not os.path.exists(csv_path):
            logger.info(f"CSV not found, downloading: {statsDataId}")
            next_key = '1'

            if self._['next_key']:
                while next_key != '-1':
                    next_key = self.get_all_data(statsDataId, next_key)
                    if next_key is None:
                        raise Exception(f"Failed to download data for {statsDataId}")
                    logger.info(f"Next key: {next_key}")
            else:
                self.get_all_data(statsDataId, next_key)

            self.convert_raw_json_to_csv(statsDataId)

        # CSVの読み込み
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 2行目(キー行)を除外
            lines = [lines[0]] + lines[2:]

            if cmd == 'head':
                result = ''.join(lines[:6])  # ヘッダー + 5行
            elif cmd == 'tail':
                result = ''.join([lines[0]] + lines[-5:])  # ヘッダー + 最後の5行
            else:
                result = ''.join(lines)

            return result
        except Exception as e:
            logger.error(f"Failed to read CSV: {e}")
            raise

    def error(self, txt):
        logger.error(txt)
        return txt

    def get_output(self, data, output_type):
        def get_tmp_data(tmp_data_0_j, tmp_data_i_j):
            if re.match(r'^\$\d+$', tmp_data_0_j) or tmp_data_0_j == '$':
                return float(tmp_data_i_j) if tmp_data_i_j != '' else None
            else:
                return tmp_data_i_j

        if output_type == 'csv':
            return data
        elif output_type == 'rjson':
            tmp_data = list(csv.reader(io.StringIO(data.strip())))
            data = []
            for i in range(1, len(tmp_data)):
                row_data = {}
                for j in range(len(tmp_data[i])):
                    row_data[tmp_data[0][j]] = get_tmp_data(
                        tmp_data[0][j], tmp_data[i][j])
                data.append(row_data)
            return json.dumps(data, ensure_ascii=False)
        elif output_type == 'cjson':
            tmp_data = list(csv.reader(io.StringIO(data.strip())))
            data = {}
            for i in range(len(tmp_data[0])):
                data[tmp_data[0][i]] = [
                    get_tmp_data(tmp_data[0][i], tmp_data[j][i])
                    for j in range(1, len(tmp_data))
                ]
            return json.dumps(data, ensure_ascii=False)
        else:
            return self.error(self.msg['check-extension'])

    def mimetype(self, ext):
        mt = 'text/plain' if ext == 'csv' else 'application/json'
        if request.args.get('dl') == 'true':
            mt = 'application/octet-stream'
        return mt

    def response(self, res, ext):
        return Response(res, mimetype=self.mimetype(ext), headers=self.header)
