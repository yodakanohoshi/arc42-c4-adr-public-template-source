# Mermaidサンプル

このページは、Markdownの ` ```mermaid ` ブロックでC4を含む各種図を記載できることを示すサンプルです。
WebサイトではブラウザがMermaidを描画し、PDFではビルド時に画像へ変換して埋め込みます。

## C4: システムコンテキスト図

```mermaid
C4Context
  title 対象システムのシステムコンテキスト
  Person(user, "利用者", "Webから業務操作を行う")
  System(target, "対象システム", "主要な業務能力を提供する")
  System_Ext(ext, "外部システム", "参照情報・処理結果を提供する")
  System_Ext(notify, "通知サービス", "利用者・運用者へ通知する")

  Rel(user, target, "業務操作", "HTTPS")
  Rel(target, ext, "参照・更新", "API / File / Event")
  Rel(target, notify, "通知配信", "API / Queue")
```

## C4: コンテナ図

```mermaid
C4Container
  title 対象システムのコンテナ図
  Person(user, "利用者")
  System_Boundary(sys, "対象システム") {
    Container(ui, "クライアントアプリ", "SPA", "操作・入力補助・結果表示")
    Container(api, "アプリケーションAPI", "HTTP", "入力検証・受付・応答整形")
    Container(core, "コアアプリケーション", "サービス", "業務ルール・トランザクション")
    ContainerDb(db, "データストア", "RDB", "業務データの永続化")
  }
  Rel(user, ui, "利用", "HTTPS")
  Rel(ui, api, "要求", "HTTPS")
  Rel(api, core, "呼び出し", "Internal API")
  Rel(core, db, "読み書き", "SQL")
```

## シーケンス図（ランタイムビュー）

```mermaid
sequenceDiagram
  participant U as 利用者
  participant A as API
  participant C as コア
  participant D as データストア
  U->>A: 業務要求
  A->>A: 入力検証
  A->>C: ユースケース実行
  C->>D: 更新
  D-->>C: 結果
  C-->>A: 応答
  A-->>U: 結果表示
```

## フローチャート（異常系の判断）

```mermaid
flowchart TD
  start([要求受信]) --> valid{入力は妥当か}
  valid -- いいえ --> reject[400で拒否]
  valid -- はい --> exec[処理実行]
  exec --> ok{成功したか}
  ok -- はい --> done([完了])
  ok -- いいえ --> retry{再試行可能か}
  retry -- はい --> exec
  retry -- いいえ --> fail[エラー応答・記録]
```
