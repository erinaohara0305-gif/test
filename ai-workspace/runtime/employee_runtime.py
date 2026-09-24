#!/usr/bin/env python3
"""AI社員の受付・重複防止・納品履歴。生成と定刻起動はAIアプリ（Codex / Claude Code）が担当する。"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid


MARKER = ".ai-employee-workspace.json"
FORMATS = {".md", ".txt", ".vtt", ".srt", ".csv", ".json", ".pdf",
           ".docx", ".mp3", ".wav", ".m4a", ".mp4", ".mov"}


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    # 同じフォルダ内の一時ファイルから置換し、不完全な状態ファイルを残さない。
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     dir=path.parent, delete=False) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def inside(root, relative):
    candidate = root / relative
    resolved = candidate.resolve()
    resolved.relative_to(root)
    for part in (candidate, *candidate.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError("作業フォルダ内のシンボリックリンクは対象外です")
    return resolved


def workspace(path):
    root = Path(path).expanduser().resolve()
    if read_json(inside(root, MARKER)).get("schema") != 1:
        raise ValueError("対応するAI社員作業フォルダではありません")
    return root


def valid_id(value):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", value):
        raise ValueError("社員IDは英小文字で始まる48文字以内の英小文字・数字・ハイフン")
    return value


def employee(root, employee_id):
    config = read_json(inside(root, f"employees/{valid_id(employee_id)}.json"))
    if config["id"] != employee_id or config["trigger"] not in {"inbox", "periodic"}:
        raise ValueError("社員設定が不正です")
    if config["delivery"] not in {"draft", "approval"}:
        raise ValueError("納品方式が不正です")
    return config


@contextmanager
def locked(root):
    lock = inside(root, "logs/.runtime-lock")
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError("履歴更新中です。繰り返す場合は実行中プロセスを確認してください")
    try:
        yield
    finally:
        lock.rmdir()


def state_path(root):
    return inside(root, "logs/state.json")


def record(job, status, note=""):
    job["status"] = status
    job["updated_at"] = now()
    job.setdefault("history", []).append(
        {"at": job["updated_at"], "status": status, "note": note})


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def source_info(root, config, source):
    path = inside(root, source)
    relative = path.relative_to(inside(root, f"inbox/{config['id']}"))
    if any(part.startswith(".") for part in relative.parts):
        raise ValueError("隠しファイルは処理しません")
    if not path.is_file() or path.suffix.lower() not in FORMATS:
        raise ValueError("素材が存在しないか受付対象外の形式です")
    return {"path": path.relative_to(root).as_posix(),
            "sha256": digest(path), "bytes": path.stat().st_size}


def identity(root, config, source=None, period=None):
    if config["trigger"] == "inbox":
        if not source or period:
            raise ValueError("素材型の社員には --source を指定してください")
        data = {"source": source_info(root, config, source)}
    else:
        if source or not period or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}", period):
            raise ValueError("定期型の社員には --period で対象期間を指定してください")
        data = {"period": period}
    key = json.dumps({"employee": config["id"], **data}, sort_keys=True)
    job_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return job_id, data


def initialize(args):
    root = Path(args.workspace).expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("作成先は空か未作成のフォルダにしてください。既存内容は上書きしません")
    package = Path(__file__).resolve().parents[1]
    assets = package / "assets"
    if not assets.is_dir():
        raise ValueError("新規作成にはスキルの scripts/ 内のスクリプトを使ってください")
    root.mkdir(parents=True, exist_ok=True)
    for directory in ("context", "employees", "workflows", "schedules", "inbox",
                      "output", "approval", "logs", "runtime"):
        (root / directory).mkdir(exist_ok=True)
    shutil.copyfile(assets / "AGENTS.template.md", root / "AGENTS.md")
    for name in ("business-profile", "audience", "offers", "brand-voice"):
        shutil.copyfile(assets / f"{name}.template.md", root / "context" / f"{name}.md")
    shutil.copyfile(Path(__file__).resolve(), root / "runtime/employee_runtime.py")
    write_json(root / MARKER, {"schema": 1, "created_at": now()})
    write_json(root / "logs/state.json", {"schema": 1, "jobs": {}})
    return {"workspace": str(root), "status": "initialized", "schedule": "not_registered"}


def add(root, args):
    identifier = valid_id(args.employee)
    if not args.name.strip() or not args.goal.strip():
        raise ValueError("名前と仕事の目的が必要です")
    config = {"id": identifier, "name": args.name, "goal": args.goal,
              "trigger": args.trigger, "delivery": args.delivery,
              "enabled": True, "max_attempts": 2}
    destinations = [inside(root, f"employees/{identifier}.json"),
                    inside(root, f"workflows/{identifier}.md"),
                    inside(root, f"schedules/{identifier}.json")]
    with locked(root):
        if any(path.exists() for path in destinations):
            raise ValueError("同名の社員または手順がすでにあります")
        write_json(destinations[0], config)
        destinations[1].write_text(
            f"# {args.name}\n\n目的: {args.goal}\n\n"
            "セットアップ時に、素材の範囲・完成形・必要なツール・納品条件を具体化してください。\n",
            encoding="utf-8")
        write_json(destinations[2], {"employee": identifier, "status": "not_registered",
                                    "automation_id": None})
        inside(root, f"inbox/{identifier}").mkdir(exist_ok=True)
    return {"employee": config, "schedule": "not_registered"}


def scan(root, args):
    config = employee(root, args.employee)
    if not config["enabled"]:
        return {"employee": args.employee, "status": "paused", "pending": []}
    state = read_json(state_path(root))
    candidates, errors = [], []
    if config["trigger"] == "periodic":
        job_id, data = identity(root, config, period=args.period)
        candidates.append((job_id, data))
    else:
        for path in sorted(inside(root, f"inbox/{args.employee}").rglob("*")):
            if path.suffix.lower() not in FORMATS or not path.is_file():
                continue
            if any(part.startswith(".") for part in path.relative_to(root).parts):
                continue
            try:
                candidates.append(identity(root, config, source=str(path)))
            except (OSError, ValueError) as error:
                errors.append({"path": str(path), "error": str(error)})
    pending, existing = [], []
    for job_id, data in candidates:
        prior = state["jobs"].get(job_id)
        item = {"job_id": job_id, **data}
        if not prior or prior["status"] == "pending":
            pending.append(item)
        else:
            existing.append({**item, "status": prior["status"]})
    return {"employee": args.employee, "pending": pending, "existing": existing,
            "errors": errors}


def claim(root, args):
    with locked(root):
        config = employee(root, args.employee)
        if not config["enabled"]:
            return {"status": "paused"}
        job_id, data = identity(root, config, args.source, args.period)
        state = read_json(state_path(root))
        previous = state["jobs"].get(job_id)
        if previous and previous["status"] != "pending":
            return {"status": "skipped", "job_id": job_id,
                    "previous_status": previous["status"]}
        job = previous or {"job_id": job_id, "employee": args.employee,
                           "attempts": 0, **data}
        if job["attempts"] >= config["max_attempts"]:
            raise ValueError("再試行上限です。原因と作業状態を確認してください")
        job["attempts"] += 1
        job["claim_token"] = uuid.uuid4().hex
        category = "approval" if config["delivery"] == "approval" else "output"
        folder = f"{category}/{args.employee}/{job_id}/attempt-{job['attempts']}"
        inside(root, folder).mkdir(parents=True, exist_ok=False)
        job["delivery_dir"] = folder
        job["delivery"] = config["delivery"]
        record(job, "running")
        state["jobs"][job_id] = job
        write_json(state_path(root), state)
    return {**job, "status": "claimed",
            "delivery_path": str(inside(root, folder))}


def transition(root, args):
    with locked(root):
        state = read_json(state_path(root))
        job = state["jobs"].get(args.job)
        if not job:
            raise ValueError("仕事IDが見つかりません")
        config = employee(root, job["employee"])
        if args.command == "retry":
            allowed = job["status"] in {"failed", "blocked"}
            if job["status"] == "running" and args.recover_interrupted:
                allowed = True
            if not allowed or job["attempts"] >= config["max_attempts"]:
                raise ValueError("この状態では再試行できないか、再試行上限です")
            job["claim_token"] = None
            record(job, "pending", args.reason)
        else:
            if job["status"] != "running" or args.token != job["claim_token"]:
                raise ValueError("実行状態またはclaimトークンが一致しません")
            if args.command == "fail":
                record(job, args.status, args.reason)
            else:
                if "source" in job:
                    current = source_info(root, config, job["source"]["path"])
                    if current != job["source"]:
                        raise ValueError("実行中に素材が変わりました。完了せずblockedを記録してください")
                files = []
                for name in args.artifact:
                    path = inside(root, name)
                    path.relative_to(inside(root, job["delivery_dir"]))
                    if not path.is_file() or path.stat().st_size == 0:
                        raise ValueError("空または存在しない成果物は納品できません")
                    files.append({"path": path.relative_to(root).as_posix(),
                                  "sha256": digest(path)})
                job["artifacts"] = files
                record(job, "waiting_approval" if job["delivery"] == "approval" else "succeeded",
                       args.summary)
        write_json(state_path(root), state)
    return job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    add_parser = sub.add_parser("add")
    add_parser.add_argument("--employee", required=True)
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--goal", required=True)
    add_parser.add_argument("--trigger", choices=["inbox", "periodic"], default="inbox")
    add_parser.add_argument("--delivery", choices=["draft", "approval"], default="draft")
    for command in ("scan", "claim"):
        child = sub.add_parser(command)
        child.add_argument("--employee", required=True)
        child.add_argument("--period")
        if command == "claim":
            child.add_argument("--source")
    for command in ("finish", "fail", "retry"):
        child = sub.add_parser(command)
        child.add_argument("--job", required=True)
        if command != "retry":
            child.add_argument("--token", required=True)
        if command == "finish":
            child.add_argument("--artifact", action="append", required=True)
            child.add_argument("--summary", required=True)
        else:
            child.add_argument("--reason", required=True)
        if command == "fail":
            child.add_argument("--status", choices=["failed", "blocked"], default="failed")
        if command == "retry":
            child.add_argument("--recover-interrupted", action="store_true")
    sub.add_parser("status")
    for command in ("pause", "resume"):
        child = sub.add_parser(command)
        child.add_argument("--employee", required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = initialize(args)
        else:
            root = workspace(args.workspace)
            if args.command == "add":
                result = add(root, args)
            elif args.command == "scan":
                result = scan(root, args)
            elif args.command == "claim":
                result = claim(root, args)
            elif args.command in {"finish", "fail", "retry"}:
                result = transition(root, args)
            elif args.command in {"pause", "resume"}:
                with locked(root):
                    config = employee(root, args.employee)
                    config["enabled"] = args.command == "resume"
                    write_json(inside(root, f"employees/{args.employee}.json"), config)
                result = {"employee": config, "note": "アプリの定期実行状態は別途変更してください"}
            else:
                result = read_json(state_path(root))
                result["employees"] = [read_json(inside(root, str(path)))
                                       for path in sorted(inside(root, "employees").glob("*.json"))]
                result["schedules"] = [read_json(inside(root, str(path)))
                                       for path in sorted(inside(root, "schedules").glob("*.json"))]
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
