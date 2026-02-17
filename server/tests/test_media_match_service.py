from app.services.media_match_service import is_visual_query, extract_query_keywords


def test_is_visual_query_true_for_campus_environment():
    assert is_visual_query("校园环境怎么样，有图片吗") is True
    assert is_visual_query("能看看宿舍和食堂视频吗") is True


def test_is_visual_query_false_for_non_visual_question():
    assert is_visual_query("今年分数线是多少") is False


def test_extract_query_keywords_basic():
    kws = extract_query_keywords("请问北师大宿舍食堂环境图片")
    assert "宿舍" in kws
    assert "食堂" in kws
