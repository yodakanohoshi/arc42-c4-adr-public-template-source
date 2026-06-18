# 8. Crosscutting Concepts

複数のBuilding Blockへ適用する共通設計方針を記載する。

## 8.1 セキュリティとアクセス制御

- 利用者、サービス、運用者を識別する方式
- 最小権限と職務分掌
- 管理操作の追加保護
- 入力検証、出力エンコーディング、依存部品管理
- 詳細は[アクセス制御マトリクス](security/authorization-matrix.md)と[脅威モデル](security/threat-model.md)へ記載する

## 8.2 インターフェース設計

- 契約のバージョニング
- 後方互換性
- Timeout、Retry、Rate Limit
- エラー形式と相関ID
- 同期・非同期の選択基準
- 正確な契約は機械可読仕様または連携台帳を正とする

## 8.3 データ管理

- データ分類と所有者
- 保存場所、保持期間、削除
- 暗号化とマスキング
- Schema変更とMigration
- 整合性、重複、履歴管理
- 非本番環境への実データ持ち込み制限

## 8.4 エラー処理と回復性

- Timeout
- RetryとBackoff
- Circuit Breaker
- 冪等性
- 重複イベント
- 失敗隔離
- 縮退動作
- 利用者向けエラーと内部エラーの分離

## 8.5 可観測性

- Logs、Metrics、Tracesの相関
- 構造化ログとCorrelation ID
- 主要SLIとDashboard
- Alertの優先度、抑制、Owner
- 個人情報や秘密情報をログへ出力しない規則

## 8.6 秘密情報・鍵・証明書

保存、アクセス権、配布、ローテーション、失効、緊急交換、監査の責任者を定義する。秘密値そのものは文書へ記載しない。

## 8.7 開発・変更管理

- CI/CDと承認手続き
- Infrastructure as Codeと手動変更の扱い
- Database Migration
- Configuration管理
- Feature Flag
- リリース、段階展開、Rollback
- 互換性の確認期間

## 8.8 時刻・地域・識別子

- タイムゾーンと日時形式
- 文字コード、言語、ロケール
- 通貨・単位
- 一意識別子の生成と公開範囲
- 並び順、丸め、精度
