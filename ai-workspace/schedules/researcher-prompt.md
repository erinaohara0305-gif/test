# リサーチ社員（researcher）定期実行の依頼文

状態: **未登録（not_registered）**。利用者が試運転の結果を確認し、開始を依頼してから登録する。

- 登録先: Claudeデスクトップアプリの定時タスク（create_scheduled_task）
- 実行時刻: 毎日 09:00（日本時間 / Asia/Tokyo）
- cron: `0 9 * * *`（PCの時刻が日本時間の場合。違う場合は換算する）
- 完了通知: 登録した会話で受け取る（notifyOnCompletion）
- 登録前に `<作業フォルダの絶対パス>` を、PC上の実際のパスに置き換える（下の「PCへの移行」を参照）

---

## 依頼文（ここから下を定時タスクに登録）

マイAI社員ビルダーのSkill（ai-employee-starter）を使い、次の社員の仕事を実行してください。この依頼は前の会話を覚えていない状態で実行されるので、下の絶対パスと社員IDだけを頼りに進めてください。

- 作業フォルダ: `<作業フォルダの絶対パス>`
- 社員ID: `researcher`（リサーチ社員）
- 業務: 初心者向けの女性向け中古戸建て投資講座の発信のために、読者に刺さる投稿ネタをWebで調べ、リサーチレポートを1本作る
- 読者: 大学生ぐらいの子どもを持ち将来が不安な40〜50代の母親、投資に積極的な30代後半の女性
- 対象と完成形: 公開Web（官公庁・公的統計 → 業界団体・大手ポータルの調査 → 報道の順に優先、直近30日中心）。投稿ネタ候補5件、各ネタに対象読者・刺さる理由（仮説と明記）・出典URLと公開日・原文で確認した事実・注意点に加え、Instagramリール案（冒頭の一言・構成・キャプション）とYouTube案（タイトル・サムネ文字・章立て）。確認できた既存動画のタイトルとURL（再生回数は実際に見られた場合のみ）。ファイル名は `投稿ネタリサーチ_YYYY-MM-DD.md`
- 実行期間の区切りとタイムゾーン: 1日1回。期間キーは実行時の日本時間（Asia/Tokyo）の日付 `YYYY-MM-DD`
- 1回の処理上限: 1レポート（ネタ5件、検索20回程度まで）

次のファイルを読んでください: `<作業フォルダの絶対パス>/AGENTS.md`、`employees/researcher.json`、`workflows/researcher.md`、`context/business-profile.md`、`context/audience.md`、`context/offers.md`、`context/brand-voice.md`、直近7回分の `output/researcher/` の納品物。
`python3 <作業フォルダの絶対パス>/runtime/employee_runtime.py --workspace <作業フォルダの絶対パス> claim --employee researcher --period <日本時間の今日の日付>` を実行し、`claimed` の時だけ処理してください。`skipped` や `paused` なら何もせず静かに終了してください。
claimが返した `delivery_path` に成果物を作り、workflows/researcher.md の納品前チェック（数字はすべて原文で確認し出典URLを付ける、事実・数字・実績・体験談を創作しない、です・ます調、成果を約束する表現なし）を点検してから `finish` してください。
記事本文を開けず数字を確認できない場合は、成功扱いにせず `fail --status blocked` で理由を記録してください。権限や接続が不足している時は回避を試みず、必要な対応を報告してください。
投稿・送信・公開・課金・元資料の削除はしないでください。パスワード・APIキー・Cookieを求めたり取得したりしないでください。
新しい納品、失敗、利用者の操作が必要な時だけ報告してください。
社員や定期実行の設定そのものを、この定期タスクが勝手に拡大・変更することはしないでください。

---

## PCへの移行（登録前に1回だけ）

1. このリポジトリ（ブランチ `claude/ai-employee-setup-xhl1dp`）をPCに取得し、`ai-workspace` フォルダの絶対パスを確認する（例: `C:\Users\<名前>\test\ai-workspace` や `/Users/<名前>/test/ai-workspace`）。
2. スキル一式をPCの `~/.claude/skills/ai-employee-starter/`（Windowsは `%USERPROFILE%\.claude\skills\ai-employee-starter\`）に置く。
3. PCのClaude Codeで「試運転が確認できたので、リサーチ社員の定期実行を登録して」と依頼する。上の依頼文のパスを置き換えて定時タスクに登録し、返された taskId を `schedules/researcher.json` に保存する。
