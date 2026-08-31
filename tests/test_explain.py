"""Tests for metric documentation and explain command."""

from bounce_house.metric_docs import METRICS, MODULES, resolve_topic


class TestMetricDocStructure:
    def test_metric_doc_has_required_fields(self):
        doc = METRICS["integrated_lufs"]
        assert doc.key == "integrated_lufs"
        assert doc.name == "Integrated LUFS"
        assert doc.module == "loudness"
        assert isinstance(doc.summary, str) and len(doc.summary) > 0
        assert isinstance(doc.explanation, str) and len(doc.explanation) > 0
        assert isinstance(doc.good_range, str) and len(doc.good_range) > 0
        assert isinstance(doc.genre_notes, str)
        assert isinstance(doc.technical, str) and len(doc.technical) > 0
        assert isinstance(doc.aliases, list)

    def test_all_loudness_metrics_documented(self):
        loudness_keys = MODULES["loudness"]
        expected = {
            "integrated_lufs",
            "loudness_range_lu",
            "true_peak_dbtp",
            "sample_peak_dbfs",
            "rms_db",
            "crest_factor_db",
            "plr_db",
            "dc_offset_db",
            "dr_score",
            "rms_curve_db",
        }
        assert set(loudness_keys) == expected

    def test_all_spectrum_metrics_documented(self):
        spectrum_keys = MODULES["spectrum"]
        expected = {
            "centroid_hz",
            "bandwidth_hz",
            "rolloff_hz",
            "flatness",
            "bands",
        }
        assert set(spectrum_keys) == expected

    def test_all_stereo_metrics_documented(self):
        stereo_keys = MODULES["stereo"]
        expected = {
            "phase_correlation",
            "mid_rms_db",
            "side_rms_db",
            "ms_ratio_db",
            "stereo_width",
            "balance_db",
            "low_block_correlation",
            "frequency_width",
            "correlation_curve",
        }
        assert set(stereo_keys) == expected

    def test_all_perceptual_metrics_documented(self):
        perceptual_keys = MODULES["perceptual"]
        expected = {"brightness", "warmth", "timbral_brightness", "timbral_warmth"}
        assert set(perceptual_keys) == expected

    def test_all_translation_metrics_documented(self):
        translation_keys = MODULES["translation"]
        expected = {"mono_loss_db", "band_mono_loss", "low_end_reliance"}
        assert set(translation_keys) == expected

    def test_every_metric_key_exists_in_METRICS(self):
        for module, keys in MODULES.items():
            for key in keys:
                assert key in METRICS, f"{key} in MODULES[{module}] but not in METRICS"

    def test_all_tuning_metrics_documented(self):
        tuning_keys = MODULES["tuning"]
        expected = {
            "tuning_deviation_cents",
            "estimated_a_hz",
            "closest_standard",
            "pitch_drift_range_cents",
            "pitch_drift_std_cents",
            "pitch_drift_trend_cents_per_min",
            "chroma_sharpness",
        }
        assert set(tuning_keys) == expected

    def test_all_qc_metrics_documented(self):
        qc_keys = MODULES["qc"]
        expected = {
            "clip_events",
            "longest_clip_run",
            "leading_silence_sec",
            "trailing_silence_sec",
        }
        assert set(qc_keys) == expected

    def test_rhythm_module_metrics_documented(self):
        rhythm_keys = MODULES["rhythm"]
        assert "tempo_bpm" in rhythm_keys
        assert "swing_ratio" in rhythm_keys
        for key in rhythm_keys:
            assert key in METRICS

    def test_no_time_signature_claim_in_docs(self):
        """The tool must never claim a notated time signature — see the design rationale."""
        for key in MODULES["rhythm"]:
            doc = METRICS[key]
            blob = (
                f"{doc.summary} {doc.explanation} {doc.good_range} "
                f"{doc.genre_notes} {doc.technical}"
            ).lower()
            assert "time signature" not in blob

    def test_modules_covers_all(self):
        assert set(MODULES.keys()) == {
            "loudness",
            "spectrum",
            "stereo",
            "translation",
            "perceptual",
            "tuning",
            "rhythm",
            "qc",
        }


class TestResolveTopic:
    def test_exact_module_match(self):
        kind, result = resolve_topic("loudness")
        assert kind == "module"
        assert result == "loudness"

    def test_exact_metric_key_match(self):
        kind, result = resolve_topic("integrated_lufs")
        assert kind == "metric"
        assert result == "integrated_lufs"

    def test_alias_match(self):
        kind, result = resolve_topic("lufs")
        assert kind == "metric"
        assert result == "integrated_lufs"

    def test_substring_match(self):
        kind, result = resolve_topic("centroid")
        assert kind == "metric"
        assert result == "centroid_hz"

    def test_case_insensitive(self):
        kind, result = resolve_topic("LUFS")
        assert kind == "metric"
        assert result == "integrated_lufs"

    def test_no_match_returns_none(self):
        kind, result = resolve_topic("xyzzy")
        assert kind == "none"
        assert isinstance(result, list)  # list of suggestions

    def test_partial_match_cent(self):
        kind, result = resolve_topic("cent")
        assert kind == "metric"
        assert result == "centroid_hz"

    def test_module_abbreviation_not_confused(self):
        # "stereo" is a module, not a metric
        kind, result = resolve_topic("stereo")
        assert kind == "module"
        assert result == "stereo"


from bounce_house.report import (  # noqa: E402
    format_explain_metric,
    format_explain_module,
    format_explain_overview,
)


class TestFormatExplainOverview:
    def test_returns_string(self):
        output = format_explain_overview()
        assert isinstance(output, str)

    def test_contains_all_module_headers(self):
        output = format_explain_overview()
        assert "Loudness" in output
        assert "Spectral" in output
        assert "Stereo" in output
        assert "Perceptual" in output

    def test_contains_metric_names(self):
        output = format_explain_overview()
        assert "Integrated LUFS" in output
        assert "Phase Correlation" in output

    def test_contains_summaries(self):
        output = format_explain_overview()
        assert "ITU-R BS.1770" in output


class TestFormatExplainModule:
    def test_loudness_module(self):
        output = format_explain_module("loudness")
        assert "Integrated LUFS" in output
        assert "Good range" in output
        assert "Genre" in output

    def test_contains_explanations(self):
        output = format_explain_module("loudness")
        assert "streaming" in output.lower() or "Streaming" in output

    def test_technical_flag(self):
        output_basic = format_explain_module("loudness", technical=False)
        output_tech = format_explain_module("loudness", technical=True)
        assert "Standard:" in output_tech
        assert "Method:" in output_tech or "Standard:" in output_tech
        # Technical output should be longer
        assert len(output_tech) > len(output_basic)


class TestFormatExplainMetric:
    def test_single_metric(self):
        output = format_explain_metric("integrated_lufs")
        assert "Integrated LUFS" in output
        assert "Good range" in output
        assert "-16 to -8 LUFS" in output

    def test_technical_flag(self):
        output = format_explain_metric("integrated_lufs", technical=True)
        assert "ITU-R BS.1770" in output
        assert "K-weighted" in output

    def test_no_technical_by_default(self):
        output = format_explain_metric("integrated_lufs", technical=False)
        assert "Standard:" not in output


from bounce_house.cli import create_parser, main  # noqa: E402


class TestExplainCLI:
    def test_explain_parser_no_args(self):
        parser = create_parser()
        args = parser.parse_args(["explain"])
        assert args.command == "explain"
        assert args.topic is None
        assert args.technical is False

    def test_explain_parser_with_topic(self):
        parser = create_parser()
        args = parser.parse_args(["explain", "loudness"])
        assert args.topic == "loudness"

    def test_explain_parser_with_technical(self):
        parser = create_parser()
        args = parser.parse_args(["explain", "lufs", "--technical"])
        assert args.technical is True

    def test_explain_no_topic_returns_0(self, capsys):
        result = main(["explain"])
        assert result == 0
        output = capsys.readouterr().out
        assert "Metric Reference" in output

    def test_explain_module_returns_0(self, capsys):
        result = main(["explain", "loudness"])
        assert result == 0
        output = capsys.readouterr().out
        assert "Integrated LUFS" in output
        assert "Good range" in output

    def test_explain_metric_returns_0(self, capsys):
        result = main(["explain", "lufs"])
        assert result == 0
        output = capsys.readouterr().out
        assert "Integrated LUFS" in output

    def test_explain_invalid_topic_returns_1(self, capsys):
        result = main(["explain", "xyzzy"])
        assert result == 1
        output = capsys.readouterr().err
        assert "not found" in output.lower() or "Unknown" in output

    def test_explain_technical_flag(self, capsys):
        main(["explain", "lufs", "--technical"])
        output = capsys.readouterr().out
        assert "Standard" in output or "Method" in output

    def test_explain_fuzzy_match(self, capsys):
        result = main(["explain", "centroid"])
        assert result == 0
        output = capsys.readouterr().out
        assert "Spectral Centroid" in output
