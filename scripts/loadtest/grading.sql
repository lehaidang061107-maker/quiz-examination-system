-- S3-10: thời gian chấm = từ lúc bài ở trạng thái nộp đến lúc có Result (NFR-PER-03), và số bài chưa chấm.
SELECT count(*) AS bai_da_cham,
       round(avg(extract(epoch FROM r.graded_at - s.submitted_at))::numeric, 3) AS tb_giay,
       round((percentile_cont(0.95) WITHIN GROUP (ORDER BY extract(epoch FROM r.graded_at - s.submitted_at)))::numeric, 3) AS p95_giay,
       round(max(extract(epoch FROM r.graded_at - s.submitted_at))::numeric, 3) AS max_giay,
       round(100.0 * count(*) FILTER (WHERE r.graded_at - s.submitted_at <= interval '5 seconds') / count(*), 2) AS pct_trong_5s
FROM submissions s JOIN results r ON r.submission_id = s.submission_id;
SELECT status, count(*) FROM submissions GROUP BY status ORDER BY status;
