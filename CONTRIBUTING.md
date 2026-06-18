# Contributing

## 変更の基本方針

- 章順は `mkdocs.yml` の `nav` で管理します。
- MarkdownはMkDocsとPandocの両方で解釈できる構文を優先します。
- 図の原本は `diagrams/*.dot` です。PNGを直接編集しません。
- 特定企業、製品、クラウド、業務ドメインへ依存する例を追加しないでください。
- 実在する資格情報、URL、ID、ログをコミットしないでください。

## 検証

```bash
docker compose run --rm --build verify
```

変更時はWebサイトとPDFの両方を確認してください。

## ライセンス

コントリビューションは `LICENSE.md` に記載されたファイル別ライセンスで提供されるものとします。
