from plugins.honeypot.engine.bot_detector import BotDetector


def test_static_detection_curl():
    detector = BotDetector()
    # Curl user agent -> Strong Bot Signal
    res = detector.analyze("1.2.3.4", "", user_agent="curl/7.68.0")
    print(f"Res: {res}")
    assert res.is_bot is True
    assert res.classification == "bot"
    assert "User-Agent" in res.reason


def test_static_detection_browser():
    detector = BotDetector()
    # Chrome user agent -> Strong Human Signal (score 0.1)
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    res = detector.analyze("1.2.3.4", "", user_agent=ua)
    print(f"Res Browser: {res}")
    assert res.is_bot is False
    assert res.classification in ("human", "likely_human")


def test_payload_pattern():
    detector = BotDetector()
    # SQLi fuzzing pattern -> Strong Bot Signal
    payload = "UNION SELECT 1,2,3 --"
    res = detector.analyze("1.2.3.4", payload, user_agent="Mozilla/5.0")
    # Should detect pattern (score 1.0 * 0.15 = 0.15)
    # UA score 0.1 * 0.25 = 0.025
    # Entropy low? payload len 21.
    # Total confidence might be mid-range but lets check signals
    assert res.signals.payload_pattern_score == 1.0


def test_no_signals():
    detector = BotDetector()
    # No UA, No Payload -> UNKNOWN
    res = detector.analyze("1.2.3.4", "", user_agent=None)  # simulates missing header
    assert res.classification == "unknown"


def test_empty_string_ua():
    detector = BotDetector()
    # Empty string UA -> Treated as suspicious (score 0.8)
    # 0.8 * 0.25 = 0.2 score.
    # Total available weight: 0.25.
    # Confidence = 0.8.
    # Should be BOT.
    res = detector.analyze("1.2.3.4", "", user_agent="")
    assert res.classification == "bot"
