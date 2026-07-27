# 🦜 Parrot (AI オーディオ分離 API ＆ ダッシュボード)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green) ![Version](https://img.shields.io/badge/Version-1.0.1-blue)

*[Spanish](README.md) | [English](README_en.md) | 🌍 **日本語***

**Parrot** は、人工知能を活用したオーディオ分離およびポストプロダクションのための強力なローカル API と Web ダッシュボードです。Demucs v4 を使用して楽曲や音声ファイルから個々のトラック (*stems*) を分離し、Whisper AI を使用して分離されたボーカルを自動文字起こしし、3バンド EQ、ノイズゲート、パンニングなどのプロフェッショナルな調整を加えて再ミックス (*Merge*) するように設計されています。

プログラムでオーディオを操作する必要がある音楽プロデューサー、ミュージシャン、コンテンツクリエイター、開発者に最適です。

## ✨ 主な機能

* **🌍 多言語サポート:**
    * インターフェースおよびドキュメントは日本語、英語、スペイン語で提供されています。
* **🎛️ 高度なオーディオ分離 (Demucs v4):**
    * 最大6つの個別のステムを抽出：**ボーカル、ドラム、ベース、ピアノ、ギター、その他**。
* **🗣️ スマート文字起こし (Whisper AI):**
    * 分離されたボーカルを文字起こしし、字幕 `.srt` ファイルおよびテキスト `.txt` ファイルを自動生成します。
* **🎧 ミキサー＆ポストプロダクション (Merge):**
    * 3バンドイコライザー（Low, Mid, High）、トラック別ボリューム調整、パンニング、ノイズゲート、最終ノーマライズ機能でステムを再統合。
* **✂️ 高速トリミング (Trim):**
    * タイムスタンプを指定して、任意のステムから特定のフラグメントを数秒で抽出。
* **🧹 ワークスペース管理:**
    * 残留一時ファイルを削除し、ディスク容量を効率的に解放する専用エンドポイント。
* **⚡ ハードウェアアクセラレーション:**
    * NVIDIA GPU (CUDA)、Apple Silicon (MPS)、CPU を自動検出し、最適なエンジンを選択できるガイダンス機能。
* **🖥️ スマートランチャー内蔵:**
    * 進行状況をリアルタイムで表示し、依存関係と `ffmpeg` バイナリを自動管理するインストーラー。

---

## 📥 ダウンロードとインストール (バイナリ)

Parrot は Windows、macOS、Linux 用にネイティブビルドされています！Python の手動設定なしですぐに使えるコンパイル済みバージョンをダウンロードできます：

### 🍎 macOS
* **アプリ / インストーラー:** [Releases](https://github.com/JJaroll/Parrot/releases) セクションからダウンロードしてください。
  > **⚠️ macOS ユーザーへの注意 (Gatekeeper):**
  > Apple Developer ID で署名されていないオープンソースアプリのため、macOS のセキュリティにより初回起動がブロックされる場合があります。ブロックされた場合は、**システム設定 > プライバシーとセキュリティ** に移動し、セキュリティセクションで **「このまま開く」** をクリックしてください。「アプリが破損しています」と表示される場合は、ターミナルで以下を実行してください：
  > ```bash
  > xattr -cr /path/to/Parrot.app
  > ```

### 🪟 Windows
* **インストーラー (.exe):** [Releases](https://github.com/JJaroll/Parrot/releases) から `Parrot_Setup_Windows.exe` をダウンロードしてください。
  > **インストール:** インストーラーを実行します。互換性のある NVIDIA GPU が検出された場合は、CUDA アクセラレーション版か CPU 版を選択できます。

### 🐧 Linux
* **ユニバーサル実行ファイル (.AppImage):** [Releases](https://github.com/JJaroll/Parrot/releases) から `Parrot_Linux.AppImage` をダウンロードしてください。
  > **インストール:** ファイルに実行権限を付与し (`chmod +x Parrot_Linux.AppImage`)、直接実行します。

---

## 🛠️ ソースコードからのビルド

開発者でソースコードを直接実行または変更したい場合：

### 前提条件
* Python 3.10 以上。
* システムにインストールされた `ffmpeg` / `ffprobe`（未検出の場合、ランチャーが `~/.parrot_studio/bin` に自動ダウンロードします）。

### 手順
1. **リポジトリのクローン:**
   ```bash
   git clone https://github.com/JJaroll/Parrot.git
   cd Parrot
   ```

2. **仮想環境の作成 (推奨):**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **依存関係のインストール:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 使い方

メインサーバーまたはランチャーを実行します:

```bash
python main.py
```
*(対話型起動アシスタントを使用する場合は `python launcher.py` を実行)*

サーバーは `http://localhost:8001` で起動します。

* **Web ダッシュボード:** ブラウザを開き、`http://localhost:8001/` にアクセスして Web インターフェースを利用します。
* **API ドキュメント (Swagger / OpenAPI):** `http://localhost:8001/docs` にアクセスして REST エンドポイントをテストできます。

---

## 📡 主なエンドポイント

| エンドポイント | メソッド | 説明 |
|---|---|---|
| `/api/v1/separate` | `POST` | オーディオ/ビデオファイルをアップロードし、ステム分離キューに追加します。 |
| `/api/v1/status/{job_id}` | `GET` | 処理ジョブのリアルタイムステータスと進行状況を確認します。 |
| `/api/v1/transcribe/{job_id}` | `POST` | 分離されたボーカルに対して AI 文字起こし (Whisper) を開始します (`.srt` / `.txt`)。 |
| `/api/v1/trim/{job_id}` | `GET` | 特定のステムから指定時間 `[start, end]` のフラグメントを切り出します。 |
| `/api/v1/merge/{job_id}` | `POST` | 選択したステムをマージし、ポストプロダクション (EQ、パン、正規化) を適用します。 |
| `/api/v1/cleanup` | `POST` | 一時作業ディレクトリをクリーンアップし、ディスク容量を解放します。 |
| `/api/v1/system-info` | `GET` | 検出されたアクセラレーションエンジン (`cuda`, `mps`, `cpu`) を表示します。 |

---

## 📁 プロジェクト構造

| ファイル / ディレクトリ | 役割・責任 |
|---|---|
| `main.py` | メインエントリポイント。FastAPI アプリケーション、REST エンドポイント、フロントエンド静的ルーティング。 |
| `launcher.py` | 仮想環境や依存関係を準備する対話型 GUI/CLI スマートランチャー。 |
| `services/separator.py` | Demucs v4 ベースのオーディオ分離エンジン (6 stems)。 |
| `services/mixer.py` | ポストプロダクション、再ミックス (*merge*)、トリミング (*trim*)、EQ エンジン。 |
| `services/transcriber.py` | Whisper AI を使用した自動文字起こしサービス。 |
| `frontend/` | 対話型 Web ダッシュボード (HTML5/CSS3/JavaScript)。 |
| `workspace/` | 元のオーディオおよび処理結果を保存するローカル一時ストレージ。 |
| `parrot_installer.iss` | Windows ネイティブインストーラー作成スクリプト (Inno Setup)。 |

---

## 🔒 プライバシーとセキュリティ

**データはすべてローカルマシン内に保持されます。**

Parrot は完全なローカルアプリケーションです。クラウドサービスとは異なり：
* **ローカル処理:** AI モデル (Demucs & Whisper) は100%ローカルハードウェア上で実行されます。
* **テレメトリなし:** 個人データ、利用データ、音声ファイルが外部サーバーに送信されることはありません。
* **完全なプライバシー:** 録音、楽曲、文字起こしデータがデバイス外に出ることはありません。

---

## 🤝 貢献

貢献を歓迎します！

1. プロジェクトを **Fork** します。
2. ブランチを作成します (`git checkout -b feature/NewFeature`)。
3. 変更をコミットします。
4. ブランチにプッシュします (`git push origin feature/NewFeature`)。
5. **Pull Request** を送信します。

---

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で提供されています - 詳細については [LICENSE](LICENSE) ファイルを参照してください。
*📝 [利用規約](TERMS.md) および [サードパーティライセンス](THIRD_PARTY_LICENSES.md) も参照してください。*

Made with ❤️ by **JJaroll**
