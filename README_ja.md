# 🦜 Parrot (Python + FastAPI)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green)

*[Español](README.md) | [English](README_en.md) | 🌍 **日本語***

**Parrot**は、オーディオの分離とポストプロダクションのための強力なローカルAPIおよびダッシュボードです。曲やオーディオファイルから個々のトラック（ステム）を分離し、AI（Whisper）を使用して文字起こしを行い、EQ、ノイズゲート、パンニングなどのプロフェッショナルな調整を加えて再ミックス（マージ）するように設計されています。

プログラムでオーディオを操作する必要がある音楽プロデューサー、ミュージシャン、コンテンツクリエイター、開発者に最適です。

## ✨ 主な機能

* **🌍 多言語サポート:**
    * ドキュメントは英語、スペイン語、日本語で利用可能です。
* **🎛️ 高度なオーディオ分離:**
    * 個別のステムを抽出します：ボーカル、ドラム、ベース、ピアノ、ギター、その他。
* **🗣️ スマート文字起こし (Whisper):**
    * 分離されたボーカルを文字起こしし、`.srt`および`.txt`ファイルを自動的に生成します。字幕に最適です。
* **🎧 ミキサー＆ポストプロダクション (Merge):**
    * ボリューム、パンニング、ノイズゲート、ベース/ミッド/トレブルのゲイン、最終的な正規化を完全に制御してステムを再統合します。
* **✂️ 高速編集 (Trim):**
    * ステムの特定のフラグメントを数秒で抽出します。
* **🧹 スペース管理:**
    * 残留ファイルを削除してワークスペースを効率的にクリーンアップするための専用エンドポイント。

---

## 🛠️ セットアップとインストール

Parrotには、重いAIモデルと依存関係のインストールを完全に自動化するネイティブな **スマートランチャー** が含まれています。

### クイックインストール (一般ユーザー向け)
1. GitHubの [Releases](../../releases) タブにアクセスし、お使いのOS用のバージョンをダウンロードします。
2. **Windows:** `Parrot_Setup_Windows.exe` を実行し、インストーラーの指示に従います（デスクトップにショートカットを作成するか選べます）。**macOS:** `Parrot.app` を開きます。**Linux:** 実行権限を付与してから `Parrot_Linux.AppImage` を実行します。
3. ランチャーは自動的にPythonをインストールし（不足している場合）、初回起動時にすべての要件をダウンロードします。対応するNVIDIA GPUを検出した場合は、CUDA対応版とCPU版のどちらを使うか確認します。
4. これで完了です！ブラウザにParrotのダッシュボードが開きます。次回からは瞬時に起動します。

### 手動インストール (開発者向け)
1. **リポジトリのクローン:**
    ```bash
    git clone https://github.com/JJaroll/Parrot.git
    cd Parrot
    ```
2. **仮想環境の作成:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Windowsの場合: .\venv\Scripts\activate
    ```
3. **依存関係のインストール:**
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 使い方

メインサーバーを実行します:

```bash
python main.py
```
サーバーは `http://0.0.0.0:8001` で起動します。

* **ダッシュボード / UI:** ブラウザを開き、`http://localhost:8001/` にアクセスしてインタラクティブなWebインターフェースを利用します。
* **API ドキュメント (Swagger):** エンドポイントをテストおよび表示するには、`http://localhost:8001/docs` にアクセスします。

## 📡 主なエンドポイント

* `POST /api/v1/separate`: オーディオファイルをアップロードし、ステム分離をキューに入れます。
* `GET /api/v1/status/{job_id}`: 分離ジョブのステータスを確認します。
* `POST /api/v1/transcribe/{job_id}`: Whisperを使用して文字起こし（デフォルトは 'vocals'）を開始します。
* `GET /api/v1/trim/{job_id}`: ステムから特定のフラグメントをトリミングします [start, end]。
* `POST /api/v1/merge/{job_id}`: ポストプロダクション機能（EQ、パンニング、正規化）を使用してステムをマージします。
* `POST /api/v1/cleanup`: 作業ディレクトリをクリーンアップし、スペースを解放します。

## 📁 プロジェクト構造

* **main.py:** エントリポイント。FastAPIアプリケーションを定義し、サービスと接続します。
* **frontend/:** インタラクティブダッシュボードのコード (HTML/JS/CSS) を含みます。
* **services/:**
  * **separator.py:** オーディオ分離ロジック。
  * **mixer.py:** トリミングと再ミックスロジック（ポストプロダクション）。
  * **transcriber.py:** オーディオ文字起こしシステム（Whisper）。
* **workspace/:** 元のオーディオファイルと処理済みジョブを保存する一時ディレクトリ。

## 🤝 貢献

貢献を歓迎します！

1. プロジェクトを **Fork** します。
2. ブランチを作成します (`git checkout -b feature/NewFeature`)。
3. 変更をコミットします。
4. ブランチにプッシュします (`git push origin feature/NewFeature`)。
5. **Pull Request** を開きます。

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下でライセンスされています - 詳細については [LICENSE](LICENSE) ファイルを参照してください。

Made with ❤️ by **JJaroll**
