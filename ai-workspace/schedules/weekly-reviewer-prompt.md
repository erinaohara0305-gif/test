# 振り返り社員（weekly-reviewer）定期実行の依頼文

状態: **未登録（not_registered）**。利用者が試運転の結果を確認し、開始を依頼してから登録する。

- 登録先: Claudeデスクトップアプリの定時タスク（create_scheduled_task）
- 実行時刻: 毎日 20:01（日本時間 / Asia/Tokyo）
- cron: `1 20 * * *`（PCの時刻が日本時間の場合。違う場合は換算する）
- 完了通知: 登録した会話で受け取る（notifyOnCompletion）
- 登録前に `<作業フォルダの絶対パス>` を、PC上の実際のパスに置き換える

---

## 依頼文（ここから下を定時タスクに登録）

マイAI社員ビルダーのSkill（ai-employee-starter）を使い、次の社員の仕事を実行してください。この依頼は前の会話を覚えていない状態で実行されるので、下の絶対パスと社員IDだけを頼りに進めてください。

- 作業フォルダ: `<作業フォルダの絶対パス>`
- 社員ID: `weekly-reviewer`（振り返り社員）
- 業務: 自社講座（初心者向けの女性向け中古戸建て投資講座）の集客のため、Instagramストーリーズの訴求内容を振り返り、閲覧率アップの施策案を作る
- 対象と完成形: `inbox/weekly-reviewer/` に届いている、実行日を含む直近7日間分のストーリーズのインサイト数値（利用者が手動で入れたテキスト・CSV・PDF・docx）を読み、投稿ごとの実績表・数値からわかること（仮説と明記）・施策案3〜5件（対象読者・意図・参考実績・注意点付き）をまとめたレポートを作る。ファイル名は `ストーリーズ振り返り_YYYY-MM-DD.md`
- 実行期間の区切りとタイムゾーン: 毎日実行。期間キーは実行日の日本時間（Asia/Tokyo）の日付 `YYYY-MM-DD`。中身は直近7日間分のinboxデータをまとめて見る
- 1回の処理上限: 1レポート（施策案3〜5件）
- データがない日: 新しいストーリーズのデータがinboxに無ければ、`fail --status blocked` で「データなし」と記録し、静かに終了する（無理に作らない）

次のファイルを読んでください: `<作業フォルダの絶対パス>/AGENTS.md`、`employees/weekly-reviewer.json`、`workflows/weekly-reviewer.md`、`context/business-profile.md`、`context/audience.md`、`context/offers.md`、`context/brand-voice.md`、直近4回分の `output/weekly-reviewer/` の納品物。
`python3 <作業フォルダの絶対パス>/runtime/employee_runtime.py --workspace <作業フォルダの絶対パス> claim --employee weekly-reviewer --period <日本時間の今日の日付>` を実行し、`claimed` の時だけ処理してください。`skipped` や `paused` なら何もせず静かに終了してください。
claimが返した `delivery_path` に成果物を作り、workflows/weekly-reviewer.md の納品前チェック（利用者提供の数値以外を創作しない、断定的な効果保証をしない、講座の実績・受講者の声を創作しない、です・ます調）を点検してから `finish` してください。
投稿・ストーリーズの作成・公開・広告出稿はしないでください。パスワード・APIキー・Cookie・Instagramのログイン情報を求めたり取得したりしないでください。
新しい納品、失敗、利用者の操作が必要な時だけ報告してください。
社員や定期実行の設定そのものを、この定期タスクが勝手に拡大・変更することはしないでください。
