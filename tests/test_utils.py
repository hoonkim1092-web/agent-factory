"""core.utils 단위 테스트."""
from __future__ import annotations

import os
os.environ.setdefault("AF_DISABLE_REGISTRY_WRITE", "1")

import pytest
from core.utils import truncate_text, clamp, clamp_ratio, median, mode, variance, std_dev, mean_absolute_deviation, zscore, range_span, chunks, flatten, percentile, normalize, cumsum, running_max, running_min, exponential_moving_average, moving_average, geometric_mean, harmonic_mean, weighted_mean, interquartile_range, covariance, pearson_correlation, spearman_correlation, kurtosis, skewness, root_mean_square
from core.utils import test_file_for as _test_file_for
from core.utils import get_external_skill_roots, get_codex_skill_roots
from core.config_paths import SKILLS_DIR


class TestTruncateText:
    def test_짧은_문자열은_그대로_반환(self):
        assert truncate_text("hello", 10) == "hello"

    def test_정확히_max_len이면_그대로_반환(self):
        assert truncate_text("hello", 5) == "hello"

    def test_초과_시_suffix_붙임(self):
        result = truncate_text("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8

    def test_커스텀_suffix(self):
        result = truncate_text("hello world", 7, suffix="--")
        assert result == "hello--"
        assert len(result) == 7

    def test_빈_문자열(self):
        assert truncate_text("", 5) == ""

    def test_none_처리(self):
        assert truncate_text(None, 5) == ""  # type: ignore[arg-type]

    def test_max_len이_suffix보다_작으면_suffix_없이_자름(self):
        result = truncate_text("abcdef", 2)
        assert result == "ab"
        assert len(result) == 2

    def test_max_len_0(self):
        assert truncate_text("abc", 0) == ""

    def test_유니코드_문자(self):
        s = "안녕하세요세계"
        result = truncate_text(s, 5)
        assert len(result) == 5
        assert result == "안녕..."


class TestClamp:
    def test_범위_내_값은_그대로(self):
        assert clamp(5, 0, 10) == 5

    def test_min_미만은_min_반환(self):
        assert clamp(-1, 0, 10) == 0

    def test_max_초과는_max_반환(self):
        assert clamp(11, 0, 10) == 10

    def test_min과_동일(self):
        assert clamp(0, 0, 10) == 0

    def test_max와_동일(self):
        assert clamp(10, 0, 10) == 10

    def test_부동소수점(self):
        assert clamp(0.5, 0.0, 1.0) == 0.5

    def test_잘못된_범위는_ValueError(self):
        with pytest.raises(ValueError):
            clamp(5, 10, 0)


class TestClampRatio:
    def test_범위_내_값은_float로_반환(self):
        result = clamp_ratio(0.5)
        assert result == 0.5
        assert isinstance(result, float)

    def test_lo_미만은_lo_반환(self):
        assert clamp_ratio(-0.5) == 0.0

    def test_hi_초과는_hi_반환(self):
        assert clamp_ratio(1.5) == 1.0

    def test_lo와_동일(self):
        assert clamp_ratio(0.0) == 0.0

    def test_hi와_동일(self):
        assert clamp_ratio(1.0) == 1.0

    def test_int_입력도_float로_반환(self):
        result = clamp_ratio(0)
        assert result == 0.0
        assert isinstance(result, float)

    def test_커스텀_범위(self):
        assert clamp_ratio(5.0, lo=-1.0, hi=10.0) == 5.0

    def test_커스텀_범위_lo_초과(self):
        assert clamp_ratio(-5.0, lo=-1.0, hi=10.0) == -1.0

    def test_커스텀_범위_hi_초과(self):
        assert clamp_ratio(20.0, lo=-1.0, hi=10.0) == 10.0

    def test_lo가_hi보다_크면_ValueError(self):
        with pytest.raises(ValueError):
            clamp_ratio(0.5, lo=1.0, hi=0.0)

    def test_lo와_hi가_같으면_그_값_반환(self):
        assert clamp_ratio(0.5, lo=0.3, hi=0.3) == 0.3


class TestMedian:
    def test_단일_요소(self):
        assert median([5]) == 5.0

    def test_홀수_개_정렬됨(self):
        assert median([1, 3, 5]) == 3.0

    def test_홀수_개_비정렬(self):
        assert median([5, 1, 3]) == 3.0

    def test_짝수_개(self):
        assert median([1, 2, 3, 4]) == 2.5

    def test_음수_포함(self):
        assert median([-3, -1, 1, 3]) == 0.0

    def test_부동소수점(self):
        assert median([1.5, 2.5, 3.5]) == 2.5

    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            median([])

    def test_중복_값(self):
        assert median([2, 2, 2]) == 2.0


class TestMode:
    def test_단일_요소(self):
        assert mode([5]) == 5.0

    def test_단일_최빈값(self):
        assert mode([1, 2, 2, 3]) == 2.0

    def test_동률이면_먼저_등장한_값(self):
        # 1과 2가 각 2번씩 — 1이 먼저 등장
        assert mode([1, 2, 1, 2, 3]) == 1.0

    def test_동률_두번째가_먼저_등장(self):
        # 3과 4가 각 2번씩 — 3이 먼저
        assert mode([5, 3, 4, 3, 4]) == 3.0

    def test_모든_값이_동일_빈도(self):
        # 1, 2, 3 모두 1번씩 → 가장 먼저 등장한 1
        assert mode([1, 2, 3]) == 1.0

    def test_부동소수점(self):
        assert mode([1.5, 2.5, 1.5, 2.5, 1.5]) == 1.5

    def test_음수_포함(self):
        assert mode([-1, -1, 2, 3]) == -1.0

    def test_정수도_float로_반환(self):
        result = mode([7, 7, 8])
        assert result == 7.0
        assert isinstance(result, float)

    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            mode([])


class TestVariance:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            variance([])

    def test_단일_원소는_0(self):
        assert variance([5]) == 0.0

    def test_정수_리스트(self):
        # mean = 3.0, squared diffs = 4 + 1 + 0 + 1 + 4 = 10, / 5 = 2.0
        assert variance([1, 2, 3, 4, 5]) == 2.0


class TestStdDev:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            std_dev([])

    def test_단일_원소는_0(self):
        assert std_dev([5]) == 0.0

    def test_정수_리스트(self):
        # variance = 2.0 → std_dev = sqrt(2.0)
        import math
        assert std_dev([1, 2, 3, 4, 5]) == math.sqrt(2.0)

    def test_부동소수점_리스트(self):
        # mean = 2.0, squared diffs = 1+0+1 = 2, var = 2/3 → std = sqrt(2/3)
        import math
        assert std_dev([1.0, 2.0, 3.0]) == math.sqrt(2.0 / 3.0)

    def test_동일_값_리스트는_0(self):
        assert std_dev([7, 7, 7, 7]) == 0.0

    def test_반환_타입은_float(self):
        result = std_dev([1, 2, 3])
        assert isinstance(result, float)


class TestMeanAbsoluteDeviation:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            mean_absolute_deviation([])

    def test_단일_원소는_0(self):
        assert mean_absolute_deviation([5]) == pytest.approx(0.0)

    def test_동일_값_리스트는_0(self):
        assert mean_absolute_deviation([7, 7, 7]) == pytest.approx(0.0)

    def test_표준_케이스(self):
        # values=[1,2,3,4,5], mean=3.0
        # |1-3|+|2-3|+|3-3|+|4-3|+|5-3| = 2+1+0+1+2=6 → 6/5=1.2
        assert mean_absolute_deviation([1, 2, 3, 4, 5]) == pytest.approx(1.2)

    def test_음수_포함(self):
        # values=[-2,-1,0,1,2], mean=0.0
        # 2+1+0+1+2=6 → 6/5=1.2
        assert mean_absolute_deviation([-2, -1, 0, 1, 2]) == pytest.approx(1.2)

    def test_두_원소(self):
        # values=[0.0, 4.0], mean=2.0 → (2+2)/2=2.0
        assert mean_absolute_deviation([0.0, 4.0]) == pytest.approx(2.0)

    def test_분산보다_작거나_같음_아닌_별개_지표(self):
        # MAD ≠ std_dev 이지만 같은 데이터에 대해 0이면 둘 다 0
        values = [3, 3, 3, 3]
        assert mean_absolute_deviation(values) == pytest.approx(0.0)
        assert std_dev(values) == pytest.approx(0.0)

    def test_반환_타입은_float(self):
        assert isinstance(mean_absolute_deviation([1, 2, 3]), float)


class TestZscore:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            zscore([])

    def test_단일_원소는_0(self):
        assert zscore([42]) == [0.0]

    def test_두_원소_대칭(self):
        result = zscore([1.0, 3.0])
        assert len(result) == 2
        assert result[0] == pytest.approx(-1.0)
        assert result[1] == pytest.approx(1.0)

    def test_평균_0_표준편차_1(self):
        import math
        result = zscore([2, 4, 4, 4, 5, 5, 7, 9])
        assert pytest.approx(sum(result), abs=1e-9) == 0.0
        assert pytest.approx(math.sqrt(sum(z ** 2 for z in result) / len(result)), abs=1e-9) == 1.0

    def test_동일_값은_모두_0(self):
        result = zscore([5, 5, 5])
        assert all(z == 0.0 for z in result)

    def test_반환_길이_동일(self):
        values = [1, 2, 3, 4, 5]
        assert len(zscore(values)) == len(values)

    def test_반환_타입은_float(self):
        result = zscore([1, 2, 3])
        assert all(isinstance(z, float) for z in result)

    def test_음수_포함(self):
        result = zscore([-1, 0, 1])
        assert result[1] == pytest.approx(0.0)
        assert result[0] == pytest.approx(-result[2])


class TestRangeSpan:
    def test_단일_요소는_0(self):
        assert range_span([5]) == 0.0

    def test_정수_리스트(self):
        assert range_span([1, 2, 3, 4, 5]) == 4.0

    def test_부동소수점_리스트(self):
        assert range_span([1.5, 2.5, 4.0]) == 2.5

    def test_음수_포함(self):
        assert range_span([-3, -1, 2, 5]) == 8.0

    def test_모두_음수(self):
        assert range_span([-5, -2, -10]) == 8.0

    def test_동일_값_리스트는_0(self):
        assert range_span([7, 7, 7, 7]) == 0.0

    def test_비정렬_입력(self):
        assert range_span([3, 9, 1, 5, 2]) == 8.0

    def test_반환_타입은_float(self):
        result = range_span([1, 2, 3])
        assert isinstance(result, float)

    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            range_span([])


class TestChunks:
    def test_빈_리스트(self):
        assert chunks([], 3) == []

    def test_균등_분할(self):
        assert chunks([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    def test_나머지_발생(self):
        assert chunks([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

    def test_n이_리스트보다_크면_단일_청크(self):
        assert chunks([1, 2], 10) == [[1, 2]]

    def test_n_1이면_ValueError(self):
        with pytest.raises(ValueError):
            chunks([1, 2, 3], 0)


class TestFlatten:
    def test_빈_리스트(self):
        assert flatten([]) == []

    def test_이미_평탄_리스트(self):
        assert flatten([1, 2, 3]) == [1, 2, 3]

    def test_1단계_중첩(self):
        assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]

    def test_2단계_이상은_1단계만_평탄화(self):
        assert flatten([[1, [2, 3]], [4]]) == [1, [2, 3], 4]

    def test_혼합_타입(self):
        assert flatten([[1, 2], 3, "a"]) == [1, 2, 3, "a"]


class TestTestFileFor:
    def test_core_모듈(self):
        assert _test_file_for("core/dogfood.py") == "tests/test_dogfood.py"

    def test_scripts_모듈(self):
        assert _test_file_for("scripts/review_gate.py") == "tests/test_review_gate.py"

    def test_비파이썬_파일은_None(self):
        assert _test_file_for("docs/README.md") is None

    def test_루트_py는_None(self):
        assert _test_file_for("run_factory_cli.py") is None

    def test_중첩_경로는_None(self):
        assert _test_file_for("core/sub/foo.py") is None

    def test_백슬래시_경로(self):
        assert _test_file_for("core\\utils.py") == "tests/test_utils.py"

    def test_세미콜론_stem은_None(self):
        assert _test_file_for("core/evil;cmd.py") is None

    def test_파이프_stem은_None(self):
        assert _test_file_for("core/a|b.py") is None

    def test_달러_stem은_None(self):
        assert _test_file_for("core/$var.py") is None

    def test_대시와_점_포함_stem은_허용(self):
        assert _test_file_for("core/my-module.v2.py") == "tests/test_my-module.v2.py"


class TestNormalize:
    def test_빈_리스트는_빈_리스트_반환(self):
        assert normalize([]) == []

    def test_단일_요소는_0(self):
        assert normalize([42.0]) == [0.0]

    def test_모든_값이_동일하면_모두_0(self):
        assert normalize([5.0, 5.0, 5.0]) == [0.0, 0.0, 0.0]

    def test_두_원소(self):
        result = normalize([0.0, 10.0])
        assert result == pytest.approx([0.0, 1.0])

    def test_정규화_결과_범위(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = normalize(values)
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(1.0)

    def test_중간값_보간(self):
        result = normalize([0.0, 5.0, 10.0])
        assert result == pytest.approx([0.0, 0.5, 1.0])

    def test_음수_포함(self):
        result = normalize([-10.0, 0.0, 10.0])
        assert result == pytest.approx([0.0, 0.5, 1.0])

    def test_비정렬_입력(self):
        result = normalize([10.0, 0.0, 5.0])
        assert result == pytest.approx([1.0, 0.0, 0.5])

    def test_반환_길이_동일(self):
        values = [3.0, 1.0, 4.0, 1.0, 5.0]
        assert len(normalize(values)) == len(values)

    def test_반환_타입은_float(self):
        result = normalize([1.0, 2.0, 3.0])
        assert all(isinstance(v, float) for v in result)

    def test_정수_입력도_동작(self):
        result = normalize([0, 5, 10])
        assert result == pytest.approx([0.0, 0.5, 1.0])


class TestPercentile:
    def test_경계값_p0(self):
        assert percentile([3, 1, 2], 0.0) == pytest.approx(1.0)

    def test_경계값_p100(self):
        assert percentile([3, 1, 2], 100.0) == pytest.approx(3.0)

    def test_중앙값_p50_홀수(self):
        assert percentile([1, 2, 3, 4, 5], 50.0) == pytest.approx(3.0)

    def test_중앙값_p50_짝수(self):
        assert percentile([1, 2, 3, 4], 50.0) == pytest.approx(2.5)

    def test_비정렬_입력(self):
        assert percentile([5, 1, 4, 2, 3], 25.0) == pytest.approx(2.0)

    def test_선형_보간(self):
        # sorted [0, 10], p=25 → idx=0.25, 0*(0.75)+10*(0.25)=2.5
        assert percentile([10, 0], 25.0) == pytest.approx(2.5)

    def test_음수_포함(self):
        assert percentile([-4, -2, 0, 2, 4], 50.0) == pytest.approx(0.0)

    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            percentile([], 50.0)

    def test_p_음수는_ValueError(self):
        with pytest.raises(ValueError):
            percentile([1, 2, 3], -1.0)

    def test_p_100초과는_ValueError(self):
        with pytest.raises(ValueError):
            percentile([1, 2, 3], 100.1)

    def test_반환_타입은_float(self):
        assert isinstance(percentile([1, 2, 3], 50.0), float)


class TestCumsum:
    def test_빈_리스트는_빈_리스트_반환(self):
        assert cumsum([]) == []

    def test_단일_요소(self):
        assert cumsum([5]) == [5.0]

    def test_정수_리스트(self):
        assert cumsum([1, 2, 3, 4]) == [1.0, 3.0, 6.0, 10.0]

    def test_부동소수점_리스트(self):
        result = cumsum([1.5, 2.5, 3.0])
        assert result == pytest.approx([1.5, 4.0, 7.0])

    def test_음수_포함(self):
        assert cumsum([1, -2, 3, -4]) == [1.0, -1.0, 2.0, -2.0]

    def test_0_포함(self):
        assert cumsum([0, 0, 5]) == [0.0, 0.0, 5.0]

    def test_반환_길이_입력과_동일(self):
        values = [3, 1, 4, 1, 5]
        assert len(cumsum(values)) == len(values)

    def test_반환_타입은_float(self):
        result = cumsum([1, 2, 3])
        assert all(isinstance(v, float) for v in result)

    def test_마지막_값은_전체_합(self):
        values = [10, 20, 30]
        assert cumsum(values)[-1] == pytest.approx(sum(values))


class TestRunningMax:
    def test_빈_리스트는_빈_리스트_반환(self):
        assert running_max([]) == []

    def test_단일_요소(self):
        assert running_max([5]) == [5]

    def test_증가_수열(self):
        assert running_max([1, 2, 3, 4]) == [1, 2, 3, 4]

    def test_감소_수열은_첫_값_유지(self):
        assert running_max([4, 3, 2, 1]) == [4, 4, 4, 4]

    def test_혼합_수열(self):
        assert running_max([1, 3, 2, 5, 4]) == [1, 3, 3, 5, 5]

    def test_음수_포함(self):
        assert running_max([-3, -5, -1, -2]) == [-3, -3, -1, -1]

    def test_중복_값(self):
        assert running_max([2, 2, 2]) == [2, 2, 2]

    def test_부동소수점_리스트(self):
        assert running_max([1.5, 0.5, 3.0, 2.0]) == [1.5, 1.5, 3.0, 3.0]

    def test_반환_길이_입력과_동일(self):
        values = [3, 1, 4, 1, 5]
        assert len(running_max(values)) == len(values)

    def test_정수_타입_보존(self):
        # 반환 타입은 입력 타입을 보존한다 — 정수 입력은 정수로 유지
        result = running_max([1, 3, 2])
        assert all(isinstance(v, int) for v in result)

    def test_마지막_값은_전체_최댓값(self):
        values = [3, 7, 2, 9, 4]
        assert running_max(values)[-1] == max(values)


class TestRunningMin:
    def test_빈_리스트는_빈_리스트_반환(self):
        assert running_min([]) == []

    def test_단일_요소(self):
        assert running_min([5]) == [5]

    def test_감소_수열(self):
        assert running_min([4, 3, 2, 1]) == [4, 3, 2, 1]

    def test_증가_수열은_첫_값_유지(self):
        assert running_min([1, 2, 3, 4]) == [1, 1, 1, 1]

    def test_혼합_수열(self):
        assert running_min([5, 3, 4, 1, 2]) == [5, 3, 3, 1, 1]

    def test_음수_포함(self):
        assert running_min([-1, -5, -3, -2]) == [-1, -5, -5, -5]

    def test_중복_값(self):
        assert running_min([2, 2, 2]) == [2, 2, 2]

    def test_부동소수점_리스트(self):
        assert running_min([3.0, 1.5, 2.0, 0.5]) == [3.0, 1.5, 1.5, 0.5]

    def test_반환_길이_입력과_동일(self):
        values = [3, 1, 4, 1, 5]
        assert len(running_min(values)) == len(values)

    def test_정수_타입_보존(self):
        result = running_min([3, 1, 2])
        assert all(isinstance(v, int) for v in result)

    def test_마지막_값은_전체_최솟값(self):
        values = [3, 7, 2, 9, 4]
        assert running_min(values)[-1] == min(values)


class TestMovingAverage:
    def test_빈_리스트는_빈_리스트_반환(self):
        assert moving_average([], 3) == []

    def test_window_1은_원소별_float_캐스트(self):
        assert moving_average([1, 2, 3], 1) == [1.0, 2.0, 3.0]

    def test_window가_길이보다_크면_누진_평균(self):
        result = moving_average([1, 2, 3], 5)
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(1.5)
        assert result[2] == pytest.approx(2.0)

    def test_window가_길이와_같으면_단일_통과_평균(self):
        result = moving_average([1, 2, 3], 3)
        assert len(result) == 1 or result[-1] == pytest.approx(2.0)
        assert result[-1] == pytest.approx(2.0)

    def test_정수_입력은_float_반환(self):
        result = moving_average([4, 8, 6], 2)
        assert all(isinstance(v, float) for v in result)

    def test_부동소수점_정밀도(self):
        result = moving_average([1.0, 2.0, 3.0], 2)
        assert result == pytest.approx([1.0, 1.5, 2.5])

    def test_음수값(self):
        result = moving_average([-3, -1, -2], 2)
        assert result == pytest.approx([-3.0, -2.0, -1.5])

    def test_window_1_미만이면_ValueError(self):
        with pytest.raises(ValueError):
            moving_average([1, 2, 3], 0)


class TestGeometricMean:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            geometric_mean([])

    def test_음수_값이면_ValueError(self):
        with pytest.raises(ValueError):
            geometric_mean([1, 2, -3])

    def test_단일_요소(self):
        assert geometric_mean([4.0]) == pytest.approx(4.0)

    def test_양수_정수_2개(self):
        # geometric_mean([4, 9]) = sqrt(36) = 6.0
        assert geometric_mean([4, 9]) == pytest.approx(6.0)

    def test_세_요소(self):
        # geometric_mean([2, 8, 4]) = (64)^(1/3) = 4.0
        assert geometric_mean([2, 8, 4]) == pytest.approx(4.0)

    def test_모두_같은_값은_그_값_반환(self):
        assert geometric_mean([5, 5, 5]) == pytest.approx(5.0)

    def test_0_포함이면_0_반환(self):
        assert geometric_mean([0, 4, 9]) == pytest.approx(0.0)

    def test_부동소수점_입력(self):
        # geometric_mean([1.0, 100.0]) = 10.0
        assert geometric_mean([1.0, 100.0]) == pytest.approx(10.0)

    def test_반환_타입은_float(self):
        assert isinstance(geometric_mean([4, 9]), float)

    def test_산술평균보다_작거나_같음(self):
        values = [1, 2, 3, 4, 5]
        assert geometric_mean(values) <= sum(values) / len(values)


class TestHarmonicMean:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            harmonic_mean([])

    def test_0_값이면_ValueError(self):
        with pytest.raises(ValueError):
            harmonic_mean([1, 0, 3])

    def test_음수_값이면_ValueError(self):
        with pytest.raises(ValueError):
            harmonic_mean([1, -2, 3])

    def test_단일_요소(self):
        assert harmonic_mean([5.0]) == pytest.approx(5.0)

    def test_모두_같은_값은_그_값_반환(self):
        assert harmonic_mean([4, 4, 4]) == pytest.approx(4.0)

    def test_두_원소_표준(self):
        # HM([1, 4]) = 2 / (1/1 + 1/4) = 2 / 1.25 = 1.6
        assert harmonic_mean([1, 4]) == pytest.approx(1.6)

    def test_세_원소(self):
        # HM([1, 2, 4]) = 3 / (1 + 0.5 + 0.25) = 3 / 1.75 ≈ 1.7142...
        assert harmonic_mean([1, 2, 4]) == pytest.approx(12.0 / 7.0)

    def test_반환_타입은_float(self):
        assert isinstance(harmonic_mean([1, 2, 3]), float)

    def test_산술평균_이하(self):
        values = [1, 2, 3, 4, 5]
        assert harmonic_mean(values) <= sum(values) / len(values)

    def test_기하평균_이하(self):
        values = [1, 2, 3, 4, 5]
        assert harmonic_mean(values) <= geometric_mean(values)

    def test_부동소수점_입력(self):
        # HM([2.0, 2.0]) = 2.0
        assert harmonic_mean([2.0, 2.0]) == pytest.approx(2.0)


class TestWeightedMean:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            weighted_mean([], [])

    def test_길이_불일치는_ValueError(self):
        with pytest.raises(ValueError):
            weighted_mean([1, 2, 3], [1, 2])

    def test_음수_weight는_ValueError(self):
        with pytest.raises(ValueError):
            weighted_mean([1, 2], [1, -1])

    def test_weight_합이_0이면_ValueError(self):
        with pytest.raises(ValueError):
            weighted_mean([1, 2], [0, 0])

    def test_균등_weight는_산술평균과_동일(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        weights = [1.0, 1.0, 1.0, 1.0, 1.0]
        assert weighted_mean(values, weights) == pytest.approx(3.0)

    def test_단일_요소(self):
        assert weighted_mean([7.0], [1.0]) == pytest.approx(7.0)

    def test_두_원소_동등_가중(self):
        assert weighted_mean([0.0, 10.0], [1.0, 1.0]) == pytest.approx(5.0)

    def test_첫_원소에_집중_가중(self):
        assert weighted_mean([0.0, 10.0], [9.0, 1.0]) == pytest.approx(1.0)

    def test_마지막_원소에_집중_가중(self):
        assert weighted_mean([0.0, 10.0], [1.0, 9.0]) == pytest.approx(9.0)

    def test_정수_입력도_float_반환(self):
        result = weighted_mean([2, 4], [1, 3])
        assert isinstance(result, float)
        assert result == pytest.approx(3.5)

    def test_0_weight_원소는_기여_없음(self):
        assert weighted_mean([100.0, 5.0], [0.0, 1.0]) == pytest.approx(5.0)

    def test_비정규화_weight도_동작(self):
        # values=[1, 3], weights=[2, 6] → (1*2+3*6)/8 = 20/8 = 2.5
        assert weighted_mean([1.0, 3.0], [2.0, 6.0]) == pytest.approx(2.5)


class TestInterquartileRange:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            interquartile_range([])

    def test_단일_요소는_0(self):
        assert interquartile_range([5]) == pytest.approx(0.0)

    def test_모든_동일값은_0(self):
        assert interquartile_range([3, 3, 3, 3]) == pytest.approx(0.0)

    def test_5원소_표준(self):
        # sorted=[1,2,3,4,5], Q1=idx 1.0→s[1]=2.0, Q3=idx 3.0→s[3]=4.0, IQR=2.0
        assert interquartile_range([1, 2, 3, 4, 5]) == pytest.approx(2.0)

    def test_3원소(self):
        # sorted=[1,2,3], Q1=idx 0.5→1.5, Q3=idx 1.5→2.5, IQR=1.0
        assert interquartile_range([1, 2, 3]) == pytest.approx(1.0)

    def test_비정렬_입력(self):
        assert interquartile_range([5, 1, 4, 2, 3]) == pytest.approx(2.0)

    def test_음수_포함(self):
        # sorted=[-4,-2,0,2,4], Q1=idx 1.0→-2.0, Q3=idx 3.0→2.0, IQR=4.0
        assert interquartile_range([-4, -2, 0, 2, 4]) == pytest.approx(4.0)

    def test_부동소수점_입력(self):
        # sorted=[1.0,2.0,3.0,4.0], Q1=idx 0.75→1.75, Q3=idx 2.25→3.25, IQR=1.5
        assert interquartile_range([1.0, 2.0, 3.0, 4.0]) == pytest.approx(1.5)

    def test_반환_타입은_float(self):
        assert isinstance(interquartile_range([1, 2, 3, 4, 5]), float)


class TestCovariance:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            covariance([], [])

    def test_길이_불일치는_ValueError(self):
        with pytest.raises(ValueError):
            covariance([1, 2], [1])

    def test_단일_원소는_0(self):
        assert covariance([5], [5]) == pytest.approx(0.0)

    def test_양수_공분산(self):
        # xs와 ys가 같이 증가하면 양수 공분산
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 5.0, 4.0, 5.0]
        assert covariance(xs, ys) > 0

    def test_음수_공분산(self):
        # xs가 증가할 때 ys가 감소하면 음수 공분산
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert covariance(xs, ys) < 0

    def test_자기자신과의_공분산은_분산과_동일(self):
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        assert covariance(values, values) == pytest.approx(variance(values))

    def test_두_원소_표준(self):
        xs = [1.0, 3.0]
        ys = [2.0, 4.0]
        # mean_x=2.0, mean_y=3.0
        # (1-2)*(2-3) + (3-2)*(4-3) = 1+1=2; / 2 = 1.0
        assert covariance(xs, ys) == pytest.approx(1.0)

    def test_반환_타입은_float(self):
        assert isinstance(covariance([1, 2, 3], [4, 5, 6]), float)


class TestPearsonCorrelation:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            pearson_correlation([], [])

    def test_길이_불일치는_ValueError(self):
        with pytest.raises(ValueError):
            pearson_correlation([1, 2], [1])

    def test_완전_양수_상관(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        assert pearson_correlation(xs, ys) == pytest.approx(1.0)

    def test_완전_음수_상관(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert pearson_correlation(xs, ys) == pytest.approx(-1.0)

    def test_상수_xs는_0(self):
        assert pearson_correlation([3.0, 3.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(0.0)

    def test_상수_ys는_0(self):
        assert pearson_correlation([1.0, 2.0, 3.0], [5.0, 5.0, 5.0]) == pytest.approx(0.0)

    def test_단일_원소는_0(self):
        assert pearson_correlation([5], [5]) == pytest.approx(0.0)

    def test_범위는_마이너스1에서_1_사이(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 5.0, 4.0, 5.0]
        r = pearson_correlation(xs, ys)
        assert -1.0 <= r <= 1.0

    def test_반환_타입은_float(self):
        assert isinstance(pearson_correlation([1, 2, 3], [4, 5, 6]), float)


class TestGetExternalSkillRoots:
    def test_반환값은_리스트(self):
        result = get_external_skill_roots()
        assert isinstance(result, list)

    def test_반환_경로는_모두_절대경로(self):
        for path in get_external_skill_roots():
            assert os.path.isabs(path), f"절대 경로가 아님: {path}"

    def test_중복_없음(self):
        result = get_external_skill_roots()
        lower = [p.lower() for p in result]
        assert len(lower) == len(set(lower)), "중복 경로가 존재합니다"

    def test_extra_roots_포함(self, tmp_path):
        extra = str(tmp_path / "extra_skills")
        result = get_external_skill_roots(extra_roots=[extra])
        assert any(os.path.normcase(p) == os.path.normcase(os.path.normpath(os.path.abspath(extra))) for p in result)

    def test_extra_roots_중복_제거(self, tmp_path):
        extra = str(tmp_path / "dup_skills")
        result = get_external_skill_roots(extra_roots=[extra, extra])
        matched = [p for p in result if os.path.normcase(p) == os.path.normcase(os.path.normpath(os.path.abspath(extra)))]
        assert len(matched) == 1

    def test_env_AGENT_CODEX_SKILL_DIRS_반영(self, tmp_path, monkeypatch):
        extra = str(tmp_path / "codex_env_skills")
        monkeypatch.setenv("AGENT_CODEX_SKILL_DIRS", extra)
        monkeypatch.delenv("AGENT_CLAUDE_SKILL_DIRS", raising=False)
        result = get_external_skill_roots()
        assert any(os.path.normcase(p) == os.path.normcase(os.path.normpath(os.path.abspath(extra))) for p in result)

    def test_env_AGENT_CLAUDE_SKILL_DIRS_반영(self, tmp_path, monkeypatch):
        extra = str(tmp_path / "claude_env_skills")
        monkeypatch.setenv("AGENT_CLAUDE_SKILL_DIRS", extra)
        monkeypatch.delenv("AGENT_CODEX_SKILL_DIRS", raising=False)
        result = get_external_skill_roots()
        assert any(os.path.normcase(p) == os.path.normcase(os.path.normpath(os.path.abspath(extra))) for p in result)

    def test_CODEX_HOME_env_반영(self, tmp_path, monkeypatch):
        codex_home = str(tmp_path / "codex_home")
        monkeypatch.setenv("CODEX_HOME", codex_home)
        result = get_external_skill_roots()
        expected = os.path.normcase(os.path.normpath(os.path.join(codex_home, "skills")))
        assert any(os.path.normcase(p) == expected for p in result)

    def test_AF_SELF_RUN_SKILLS_DIR_제외(self, monkeypatch):
        monkeypatch.setenv("AF_SELF_RUN", "1")
        result = get_external_skill_roots()
        skills_dir_norm = os.path.normcase(os.path.normpath(SKILLS_DIR))
        assert not any(os.path.normcase(p) == skills_dir_norm for p in result)

    def test_AF_SELF_RUN_미설정시_SKILLS_DIR_포함(self, monkeypatch):
        monkeypatch.delenv("AF_SELF_RUN", raising=False)
        result = get_external_skill_roots()
        skills_dir_norm = os.path.normcase(os.path.normpath(SKILLS_DIR))
        assert any(os.path.normcase(p) == skills_dir_norm for p in result)

    def test_Windows에서_etc_codex_skills_없음(self):
        if os.name != "nt":
            pytest.skip("Windows 전용 테스트")
        result = get_external_skill_roots()
        assert not any("/etc/codex/skills" in p for p in result)

    def test_get_codex_skill_roots_alias(self):
        assert get_codex_skill_roots is get_external_skill_roots


class TestSpearmanCorrelation:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            spearman_correlation([], [])

    def test_길이_불일치는_ValueError(self):
        with pytest.raises(ValueError):
            spearman_correlation([1, 2], [1])

    def test_완전_양수_상관(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        assert spearman_correlation(xs, ys) == pytest.approx(1.0)

    def test_완전_음수_상관(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert spearman_correlation(xs, ys) == pytest.approx(-1.0)

    def test_상수_xs는_0(self):
        assert spearman_correlation([3.0, 3.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(0.0)

    def test_단일_원소는_0(self):
        assert spearman_correlation([5], [5]) == pytest.approx(0.0)

    def test_범위는_마이너스1에서_1_사이(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 5.0, 4.0, 5.0]
        r = spearman_correlation(xs, ys)
        assert -1.0 <= r <= 1.0

    def test_동점_처리(self):
        xs = [1.0, 1.0, 3.0, 3.0]
        ys = [1.0, 2.0, 3.0, 4.0]
        r = spearman_correlation(xs, ys)
        assert -1.0 <= r <= 1.0

    def test_반환_타입은_float(self):
        assert isinstance(spearman_correlation([1, 2, 3], [4, 5, 6]), float)


class TestKurtosis:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            kurtosis([])

    def test_단일_원소는_ValueError(self):
        with pytest.raises(ValueError):
            kurtosis([5.0])

    def test_동일값_목록은_ValueError(self):
        with pytest.raises(ValueError):
            kurtosis([3.0, 3.0, 3.0])

    def test_두_원소_분포는_마이너스2(self):
        assert kurtosis([0.0, 1.0]) == pytest.approx(-2.0)

    def test_균등_분포는_음수_첨도(self):
        assert kurtosis([1.0, 2.0, 3.0, 4.0, 5.0]) == pytest.approx(-1.3)

    def test_대칭_선형_분포(self):
        assert kurtosis([-2.0, -1.0, 0.0, 1.0, 2.0]) == pytest.approx(-1.3)

    def test_고첨도_분포는_양수(self):
        values = [0.0] * 9 + [10.0]
        assert kurtosis(values) > 0.0

    def test_공식_검증(self):
        # [0,0,0,1]: kurtosis = 7/3 - 3 = -2/3
        assert kurtosis([0.0, 0.0, 0.0, 1.0]) == pytest.approx(-2.0 / 3.0)

    def test_반환_타입은_float(self):
        assert isinstance(kurtosis([1, 2, 3, 4, 5]), float)


class TestSkewness:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            skewness([])

    def test_단일_원소는_0(self):
        assert skewness([5]) == 0.0

    def test_동일값_목록은_0(self):
        assert skewness([3, 3, 3]) == 0.0

    def test_대칭_분포는_0(self):
        assert skewness([1, 2, 3]) == pytest.approx(0.0)

    def test_오른쪽_꼬리는_양수(self):
        # [0,0,0,0,1]: 큰 양의 이상치 → 양수 왜도 1.5
        assert skewness([0, 0, 0, 0, 1]) == pytest.approx(1.5)

    def test_왼쪽_꼬리는_음수(self):
        # [0,1,1,1,1]: 작은 음의 이상치 → 음수 왜도 -1.5
        assert skewness([0, 1, 1, 1, 1]) == pytest.approx(-1.5)

    def test_부호_반전_대칭(self):
        vals = [1, 2, 4, 8]
        assert skewness(vals) == pytest.approx(-skewness([-x for x in vals]))

    def test_반환_타입은_float(self):
        assert isinstance(skewness([1, 2, 3]), float)


class TestRootMeanSquare:
    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            root_mean_square([])

    def test_모두_0이면_0(self):
        assert root_mean_square([0, 0, 0]) == 0.0

    def test_단일_값은_절댓값(self):
        assert root_mean_square([5]) == pytest.approx(5.0)
        assert root_mean_square([-5]) == pytest.approx(5.0)

    def test_수동_검증(self):
        # √((3²+4²)/2) = √(25/2) = √12.5
        assert root_mean_square([3, 4]) == pytest.approx(12.5 ** 0.5)

    def test_부호_무관(self):
        assert root_mean_square([1, -2, 3]) == pytest.approx(root_mean_square([-1, 2, -3]))

    def test_반환_타입은_float(self):
        assert isinstance(root_mean_square([1, 2, 3]), float)


class TestExponentialMovingAverage:
    def test_빈_리스트는_빈_리스트(self):
        assert exponential_moving_average([], 0.5) == []

    def test_alpha_0_이하는_ValueError(self):
        with pytest.raises(ValueError):
            exponential_moving_average([1, 2, 3], 0.0)

    def test_alpha_1_초과는_ValueError(self):
        with pytest.raises(ValueError):
            exponential_moving_average([1, 2, 3], 1.1)

    def test_alpha_음수는_ValueError(self):
        with pytest.raises(ValueError):
            exponential_moving_average([1, 2, 3], -0.5)

    def test_원소_1개는_그대로_반환(self):
        assert exponential_moving_average([7], 0.3) == [7.0]

    def test_alpha_1이면_원본과_동일(self):
        vals = [1, 2, 3, 4, 5]
        result = exponential_moving_average(vals, 1.0)
        assert result == pytest.approx([float(v) for v in vals])

    def test_alpha_0_5_수동_검증(self):
        # ema[0]=1.0, ema[1]=0.5*2+0.5*1=1.5, ema[2]=0.5*3+0.5*1.5=2.25
        result = exponential_moving_average([1, 2, 3], 0.5)
        assert result == pytest.approx([1.0, 1.5, 2.25])

    def test_결과_길이는_입력_길이와_같음(self):
        vals = [10, 20, 30, 40, 50]
        assert len(exponential_moving_average(vals, 0.3)) == len(vals)

    def test_반환_타입은_float_리스트(self):
        result = exponential_moving_average([1, 2, 3], 0.5)
        assert all(isinstance(v, float) for v in result)

    def test_정수_입력도_float_반환(self):
        result = exponential_moving_average([5, 10], 0.4)
        assert result[0] == pytest.approx(5.0)
        assert result[1] == pytest.approx(0.4 * 10 + 0.6 * 5.0)
