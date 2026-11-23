"""S3-10: kịch bản đo tải theo NFR-PER-01..03 (chỉ dùng thư viện chuẩn của Python).

Mỗi sinh viên ảo: đăng nhập, xem danh sách, bắt đầu bài, tải câu hỏi, lưu một đáp án mỗi 10 giây,
rồi nộp bài; mọi bài nộp rơi vào một cửa sổ ngắn (mặc định 10 giây) như đặc tả.

    python3 scripts/loadtest/run_load.py --users 100 --duration 120 --exam 1 --out docs/loadtest/ket-qua.json
"""
import argparse
import json
import random
import re
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

PASSWORD = "LoadTest2026"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, base, stats):
        self.base, self.stats = base, stats
        self.location = None
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), NoRedirect())

    def csrf(self):
        return next((c.value for c in self.jar if c.name == "csrftoken"), "")

    def call(self, op, path, data=None, json_body=None, ok=(200, 302, 303)):
        url = self.base + path
        headers = {"Referer": url, "X-CSRFToken": self.csrf()}
        body = None
        if json_body is not None:
            body = json.dumps(json_body).encode()
            headers["Content-Type"] = "application/json"
        elif data is not None:
            body = urllib.parse.urlencode({**data, "csrfmiddlewaretoken": self.csrf()}).encode()
        request = urllib.request.Request(url, data=body, headers=headers)
        started = time.perf_counter()
        status, text = 0, ""
        try:
            with self.opener.open(request, timeout=60) as response:
                status, text = response.status, response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            status, text = error.code, error.read().decode("utf-8", "replace")
            self.location = error.headers.get("Location")
        except Exception as error:  # hết giờ chờ, bị ngắt kết nối...
            status, text = -1, str(error)
        elapsed = time.perf_counter() - started
        self.stats.add(op, elapsed, status in ok, status)
        return status, text


class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = {}

    def add(self, op, elapsed, ok, status):
        with self.lock:
            entry = self.data.setdefault(op, {"times": [], "errors": 0, "statuses": {}})
            entry["times"].append(elapsed)
            entry["errors"] += 0 if ok else 1
            entry["statuses"][status] = entry["statuses"].get(status, 0) + 1

    def summary(self):
        result = {}
        for op, entry in self.data.items():
            times = sorted(entry["times"])
            result[op] = {
                "count": len(times),
                "errors": entry["errors"],
                "error_rate_pct": round(100 * entry["errors"] / len(times), 2),
                "p50_s": round(statistics.median(times), 3),
                "p95_s": round(times[min(len(times) - 1, int(0.95 * len(times)))], 3),
                "max_s": round(times[-1], 3),
                "within_3s_pct": round(100 * sum(t <= 3 for t in times) / len(times), 2),
                "statuses": entry["statuses"],
            }
        return result


def student(index, args, stats, t_end, rng):
    client = Client(args.base, stats)
    time.sleep(rng.uniform(0, args.ramp))  # dàn đều lượt đăng nhập trong thời gian tăng tải
    client.call("login_page", "/accounts/login/")
    status, _ = client.call("login", "/accounts/login/", {"email": f"load{index}@load.example", "password": PASSWORD})
    if status not in (302, 303):
        return
    client.call("exam_list", "/attempts/")
    status, _ = client.call("start_exam", f"/attempts/{args.exam}/start/", {})
    if status not in (302, 303):
        return
    submission = re.search(r"/attempts/submission/(\d+)/", client.location or "")  # start_exam chuyển tới trang làm bài
    if submission is None:
        return
    sub_id = submission.group(1)
    status, page = client.call("take_exam", f"/attempts/submission/{sub_id}/")
    if status != 200:
        return
    version = int((re.search(r'Number\("(\d+)"\)', page) or [0, 0])[1])
    pairs = re.findall(r'value="(\d+)"\s+data-question-id="(\d+)"', page)
    options = {}
    for option_id, question_id in pairs:
        options.setdefault(question_id, []).append(option_id)
    questions = list(options)
    while time.time() + args.save_interval < t_end:
        time.sleep(args.save_interval * rng.uniform(0.9, 1.1))
        question = rng.choice(questions)
        status, text = client.call("save_answer", f"/attempts/submission/{sub_id}/save-answer/",
                                   json_body={"question_id": int(question), "option_id": int(rng.choice(options[question])), "version": version})
        if status == 200:
            version = json.loads(text)["version"]
    time.sleep(max(0, t_end - time.time()) + rng.uniform(0, args.submit_window))  # đợt nộp đồng loạt
    client.call("submit", f"/attempts/submission/{sub_id}/submit/", {})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8100")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--exam", type=int, default=1)
    parser.add_argument("--ramp", type=float, default=30, help="giây dàn đều đăng nhập")
    parser.add_argument("--duration", type=float, default=120, help="giây làm bài sau khi tăng tải")
    parser.add_argument("--save-interval", type=float, default=10)
    parser.add_argument("--submit-window", type=float, default=10)
    parser.add_argument("--out")
    args = parser.parse_args()
    stats, rng = Stats(), random.Random(7)
    t_end = time.time() + args.ramp + args.duration
    started = time.time()
    threads = [threading.Thread(target=student, args=(i, args, stats, t_end, random.Random(i))) for i in range(1, args.users + 1)]
    threading.stack_size(512 * 1024)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    report = {"args": vars(args), "wall_seconds": round(time.time() - started, 1), "ops": stats.summary()}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
