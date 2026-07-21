<p align="center">
  <a href="https://kage.ai">
    <picture>
      <source srcset="packages/console/app/src/asset/logo-ornate-dark.svg" media="(prefers-color-scheme: dark)">
      <source srcset="packages/console/app/src/asset/logo-ornate-light.svg" media="(prefers-color-scheme: light)">
      <img src="packages/console/app/src/asset/logo-ornate-light.svg" alt="KAGE logo">
    </picture>
  </a>
</p>
<p align="center">オープンソースのAIコーディングエージェント。</p>
<p align="center">
  <a href="https://kage.ai/discord"><img alt="Discord" src="https://img.shields.io/discord/1391832426048651334?style=flat-square&label=discord" /></a>
  <a href="https://www.npmjs.com/package/kage-ai"><img alt="npm" src="https://img.shields.io/npm/v/kage-ai?style=flat-square" /></a>
  <a href="https://github.com/anomalyco/kage/actions/workflows/publish.yml"><img alt="Build status" src="https://img.shields.io/github/actions/workflow/status/anomalyco/kage/publish.yml?style=flat-square&branch=dev" /></a>
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh.md">简体中文</a> |
  <a href="README.zht.md">繁體中文</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.it.md">Italiano</a> |
  <a href="README.da.md">Dansk</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.pl.md">Polski</a> |
  <a href="README.ru.md">Русский</a> |
  <a href="README.bs.md">Bosanski</a> |
  <a href="README.ar.md">العربية</a> |
  <a href="README.no.md">Norsk</a> |
  <a href="README.br.md">Português (Brasil)</a> |
  <a href="README.th.md">ไทย</a> |
  <a href="README.tr.md">Türkçe</a> |
  <a href="README.uk.md">Українська</a> |
  <a href="README.bn.md">বাংলা</a> |
  <a href="README.gr.md">Ελληνικά</a> |
  <a href="README.vi.md">Tiếng Việt</a>
</p>

[![KAGE Terminal UI](packages/web/src/assets/lander/screenshot.png)](https://kage.ai)

---

### インストール

```bash
# YOLO
curl -fsSL https://kage.ai/install | bash

# パッケージマネージャー
npm i -g kage-ai@latest        # bun/pnpm/yarn でもOK
scoop install kage             # Windows
choco install kage             # Windows
brew install anomalyco/tap/kage # macOS と Linux（推奨。常に最新）
brew install kage              # macOS と Linux（公式 brew formula。更新頻度は低め）
sudo pacman -S kage            # Arch Linux (Stable)
paru -S kage-bin               # Arch Linux (Latest from AUR)
mise use -g kage               # どのOSでも
nix run nixpkgs#kage           # または github:anomalyco/kage で最新 dev ブランチ
```

> [!TIP]
> インストール前に 0.1.x より古いバージョンを削除してください。

### デスクトップアプリ (BETA)

KAGE はデスクトップアプリとしても利用できます。[releases page](https://github.com/anomalyco/kage/releases) から直接ダウンロードするか、[kage.ai/download](https://kage.ai/download) を利用してください。

| プラットフォーム      | ダウンロード                       |
| --------------------- | ---------------------------------- |
| macOS (Apple Silicon) | `kage-desktop-mac-arm64.dmg`   |
| macOS (Intel)         | `kage-desktop-mac-x64.dmg`     |
| Windows               | `kage-desktop-windows-x64.exe` |
| Linux                 | `.deb`、`.rpm`、または AppImage    |

```bash
# macOS (Homebrew)
brew install --cask kage-desktop
# Windows (Scoop)
scoop bucket add extras; scoop install extras/kage-desktop
```

#### インストールディレクトリ

インストールスクリプトは、インストール先パスを次の優先順位で決定します。

1. `$OPENCODE_INSTALL_DIR` - カスタムのインストールディレクトリ
2. `$XDG_BIN_DIR` - XDG Base Directory Specification に準拠したパス
3. `$HOME/bin` - 標準のユーザー用バイナリディレクトリ（存在する場合、または作成できる場合）
4. `$HOME/.kage/bin` - デフォルトのフォールバック

```bash
# 例
OPENCODE_INSTALL_DIR=/usr/local/bin curl -fsSL https://kage.ai/install | bash
XDG_BIN_DIR=$HOME/.local/bin curl -fsSL https://kage.ai/install | bash
```

### Agents

KAGE には組み込みの Agent が2つあり、`Tab` キーで切り替えられます。

- **build** - デフォルト。開発向けのフルアクセス Agent
- **plan** - 分析とコード探索向けの読み取り専用 Agent
  - デフォルトでファイル編集を拒否
  - bash コマンド実行前に確認
  - 未知のコードベース探索や変更計画に最適

また、複雑な検索やマルチステップのタスク向けに **general** サブ Agent も含まれています。
内部的に使用されており、メッセージで `@general` と入力して呼び出せます。

[agents](https://kage.ai/docs/agents) の詳細はこちら。

### ドキュメント

KAGE の設定については [**ドキュメント**](https://kage.ai/docs) を参照してください。

### コントリビュート

KAGE に貢献したい場合は、Pull Request を送る前に [contributing docs](./CONTRIBUTING.md) を読んでください。

### KAGE の上に構築する

KAGE に関連するプロジェクトで、名前に "kage"（例: "kage-dashboard" や "kage-mobile"）を含める場合は、そのプロジェクトが KAGE チームによって作られたものではなく、いかなる形でも関係がないことを README に明記してください。

---

**コミュニティに参加** [Discord](https://discord.gg/kage) | [X.com](https://x.com/kage)
