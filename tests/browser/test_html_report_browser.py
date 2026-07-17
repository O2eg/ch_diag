from __future__ import annotations

from pathlib import Path

import pytest

from ch_diag.clickhouse import column_descriptor
from ch_diag.artifact import strip_artifact_metadata
from ch_diag.render.html import render_html

playwright = pytest.importorskip("playwright.sync_api")


pytestmark = pytest.mark.browser


def browser_artifact() -> dict[str, object]:
    common = {
        "section_id": "browser",
        "state": "expanded",
        "collection_status": "ok",
        "severity_level": "ok",
        "reason": None,
        "collected_at": "2026-07-16T12:00:00Z",
        "issues": {},
        "diagnostics": [],
    }
    return {
        "artifact_schema_version": 5,
        "generator": {"name": "ch_diag", "product": "ch_diag", "version": "0.8.0"},
        "content": {
            "schema_version": 5,
            "document": {
                "catalogs": {"presentation": {"units": {}}},
                "runtime_policy": {},
                "defaults": {
                    "table": {"page_size": 25},
                    "item": {"state": "collapsed", "execution_scope": "node"},
                    "section": {"state": "expanded"},
                },
                "sections": {
                    "browser": {
                        "title": "Browser checks",
                        "items": {
                            "table": {"query": "browser.table"},
                            "chart": {"metric": "browser.chart"},
                        },
                    }
                },
                "queries": {
                    "browser.table": {
                        "title": "Filterable table",
                        "variants": [],
                    }
                },
                "scripts": {},
                "metrics": {
                    "browser.chart": {
                        "title": "Browser metric",
                        "unit": "rows/s",
                    }
                },
                "python_sources": {},
                "sampler_providers": {},
                "instructions": {},
            },
            "provenance": {},
        },
        "report": {"id": "browser", "title": "Browser contract"},
        "database": {"engine": "clickhouse", "server_version": "25.8"},
        "target": {
            "execution_scope": "node",
            "cluster_name": None,
            "connection_endpoint": {"host": "127.0.0.1", "port": 9000},
            "host_scope": "collector",
        },
        "runtime": {
            "mode": "snapshots",
            "collection_mode": "remote-db-only",
            "strip_meta": False,
        },
        "display": {"table": {"page_size": 25}},
        "sections": [
            {
                "section_id": "browser",
                "title": "Browser checks",
                "state": "expanded",
                "items": ["browser.table", "browser.chart"],
            }
        ],
        "items": {
            "browser.table": {
                **common,
                "item_id": "browser.table",
                "item_key": "table",
                "title": "Filterable table",
                "source_kind": "query",
                "source_id": "browser.table",
                "result": {
                    "kind": "table",
                    "columns": [
                        column_descriptor("name", "String", [("alpha",), ("beta",)], 0),
                        column_descriptor("value", "UInt64", [(1,), (2,)], 0),
                    ],
                    "rows": [["alpha", "1"], ["beta", "2"]],
                    "row_count": 2,
                },
                "source_metadata": {
                    "tags": ["Tables"],
                    "source_text": "SELECT name, value FROM system.browser_test",
                    "source_language": "sql",
                    "instructions": {"text": "# Inspect\n\nReview the filtered rows."},
                },
            },
            "browser.chart": {
                **common,
                "item_id": "browser.chart",
                "item_key": "chart",
                "title": "Browser metric",
                "source_kind": "metric",
                "source_id": "browser.chart",
                "result": {
                    "kind": "chart",
                    "chart": {
                        "kind": "line",
                        "x_type": "datetime",
                        "unit": "rows/s",
                        "quantity": "rows",
                    },
                    "series": [
                        {
                            "name": "queries",
                            "unit": "rows/s",
                            "points": [
                                {"t": "2026-07-16T12:00:00Z", "value": 1000},
                                {"t": "2026-07-16T12:00:05Z", "value": 2500},
                                {"t": "2026-07-16T12:00:10Z", "value": 1700},
                            ],
                        }
                    ],
                    "series_count": 1,
                    "point_count": 3,
                },
                "source_metadata": {"tags": ["Snapshots"], "chart": {"kind": "line"}},
            },
        },
        "query_texts": {},
        "snapshot_schemas": {},
        "snapshots": [],
        "diagnostics": [],
    }


def launch_chromium_or_skip(playwright_context):
    try:
        return playwright_context.chromium.launch(headless=True)
    except playwright.Error as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Playwright Chromium is not installed")
        raise


def test_standalone_report_interactions_and_exports(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    report.write_text(render_html(browser_artifact()), encoding="utf-8")
    page_errors: list[str] = []
    console_errors: list[str] = []

    with playwright.sync_playwright() as context:
        browser = launch_chromium_or_skip(context)
        page = browser.new_page(accept_downloads=True)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.goto(report.as_uri(), wait_until="load")

        assert page.locator("details.item").count() == 2
        page.get_by_role("button", name="Show SQL").click()
        assert page.locator("#sourceModal").is_visible()
        assert "SELECT name" in page.locator("#sourceCode").text_content()
        page.get_by_role("button", name="Close").first.click()

        page.get_by_role("button", name="Show Instruction").click()
        assert page.locator("#instructionModal").is_visible()
        assert "Review the filtered rows" in page.locator("#instructionBody").text_content()
        page.locator("#closeInstruction").click()

        page.get_by_role("button", name="Show meta").first.click()
        assert page.locator("#metaModal").is_visible()
        page.locator("#metaRawTab").click()
        assert "browser.table" in page.locator("#metaRawCode").text_content()
        page.locator("#closeMeta").click()

        table_item = page.locator('details.item[data-item-id="browser.table"]')
        table_item.locator('input[placeholder="Filter rows"]').fill("beta")
        assert table_item.locator("tbody tr").count() == 1
        assert "beta" in table_item.locator("tbody tr").inner_text()

        page.locator("#themeToggle").check()
        assert page.locator("html").get_attribute("data-theme") == "light"

        chart = page.locator('details.item[data-item-id="browser.chart"] .echarts-chart')
        assert chart.get_attribute("data-chart-ready") == "true"
        page.evaluate("zoomEChart(echartsCharts[0], 0.5)")
        before_pan = page.evaluate("({...echartsCharts[0].zoomRange})")
        page.evaluate("enableEChartsPan(echartsCharts[0])")
        chart.scroll_into_view_if_needed()
        box = chart.bounding_box()
        assert box is not None
        page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] * 0.7, box["y"] + box["height"] * 0.5)
        page.mouse.up()
        after_pan = page.evaluate("({...echartsCharts[0].zoomRange})")
        assert after_pan != before_pan

        for extension in ("svg", "png", "csv"):
            page.evaluate("toggleEChartsExportMenu(echartsCharts[0])")
            with page.expect_download() as download_info:
                page.get_by_role("menuitem", name=f"Export {extension.upper()}").click()
            download = download_info.value
            assert download.suggested_filename.endswith("." + extension)
            assert download.path().stat().st_size > 0

        browser.close()

    assert page_errors == []
    assert console_errors == []


def test_chart_keeps_an_all_zero_series(tmp_path: Path) -> None:
    artifact = browser_artifact()
    artifact["items"]["browser.chart"]["result"]["series"][0]["points"] = [
        {"t": "2026-07-16T12:00:00Z", "value": None},
        {"t": "2026-07-16T12:00:05Z", "value": 0},
        {"t": "2026-07-16T12:00:10Z", "value": 0},
    ]
    report = tmp_path / "zero-chart.html"
    report.write_text(render_html(artifact), encoding="utf-8")

    with playwright.sync_playwright() as context:
        browser = launch_chromium_or_skip(context)
        page = browser.new_page()
        page.goto(report.as_uri(), wait_until="load")

        item = page.locator('details.item[data-item-id="browser.chart"]')
        chart = item.locator(".echarts-chart")
        assert chart.get_attribute("data-chart-ready") == "true"
        assert item.locator(".empty-state").count() == 0
        assert page.evaluate("echartsCharts[0].series[0].data.map(point => point.y)") == [
            0,
            0,
        ]
        browser.close()


def test_numeric_identifier_is_rendered_exactly_without_si_scaling(tmp_path: Path) -> None:
    artifact = browser_artifact()
    table = artifact["items"]["browser.table"]["result"]
    table["columns"] = [
        column_descriptor("normalized_query_hash", "UInt64", [], 0),
        column_descriptor("executions", "UInt64", [], 0),
    ]
    table["rows"] = [["11636551938543030549", "108"]]
    table["row_count"] = 1
    report = tmp_path / "identifier.html"
    report.write_text(render_html(artifact), encoding="utf-8")

    with playwright.sync_playwright() as context:
        browser = launch_chromium_or_skip(context)
        page = browser.new_page()
        page.goto(report.as_uri(), wait_until="load")

        cells = page.locator('details.item[data-item-id="browser.table"] tbody td')
        assert cells.nth(0).inner_text() == "11636551938543030549"
        assert cells.nth(1).inner_text() == "108"
        browser.close()


def test_strip_meta_removes_source_controls_and_payload(tmp_path: Path) -> None:
    artifact = browser_artifact()
    strip_artifact_metadata(artifact)
    rendered = render_html(artifact)
    assert "SELECT name, value FROM system.browser_test" not in rendered
    report = tmp_path / "stripped.html"
    report.write_text(rendered, encoding="utf-8")

    with playwright.sync_playwright() as context:
        browser = launch_chromium_or_skip(context)
        page = browser.new_page()
        page.goto(report.as_uri(), wait_until="load")
        assert page.get_by_role("button", name="Show SQL").count() == 0
        assert page.get_by_role("button", name="Show Instruction").count() == 0
        assert page.get_by_role("button", name="Show meta").count() == 0
        browser.close()


def test_scalar_and_dynamic_unit_metadata_render_without_helper_table_noise(
    tmp_path: Path,
) -> None:
    artifact = browser_artifact()
    scalar = artifact["items"]["browser.table"]
    scalar["item_id"] = "browser.scalar"
    scalar["item_key"] = "scalar"
    scalar["title"] = "Total RAM Capacity"
    scalar["result"] = {
        "kind": "table",
        "columns": [column_descriptor("total_ram_bytes", "UInt64", [], 0)],
        "rows": [[str(64 * 1024**3)]],
        "row_count": 1,
    }
    value = column_descriptor("value_normalized", "UInt64", [], 0)
    value.update(
        {
            "label": "Value",
            "quantity_ref": "quantity_normalized",
            "unit_ref": "unit_normalized",
        }
    )
    memory = artifact["items"]["browser.chart"]
    memory.update(
        {
            "item_id": "browser.memory",
            "item_key": "memory",
            "title": "Memory Information",
            "source_kind": "script",
            "source_id": "os.memory_info",
            "result": {
                "kind": "table",
                "columns": [
                    column_descriptor("metric", "String", [], 0),
                    value,
                    column_descriptor("unit_normalized", "String", [], 0),
                    column_descriptor("quantity_normalized", "String", [], 0),
                ],
                "rows": [["MemTotal", str(64 * 1024**3), "bytes", "data_volume"]],
                "row_count": 1,
            },
        }
    )
    artifact["items"] = {"browser.scalar": scalar, "browser.memory": memory}
    artifact["sections"][0]["items"] = ["browser.scalar", "browser.memory"]
    report = tmp_path / "scalar.html"
    report.write_text(render_html(artifact), encoding="utf-8")

    with playwright.sync_playwright() as context:
        browser = launch_chromium_or_skip(context)
        page = browser.new_page()
        page.goto(report.as_uri(), wait_until="load")

        scalar_item = page.locator('details.item[data-item-id="browser.scalar"]')
        assert scalar_item.get_attribute("data-item-type") == "scalar"
        assert scalar_item.locator('.data-type-icon[aria-label="Scalar"]').count() == 1
        assert scalar_item.locator("table").count() == 0
        assert scalar_item.locator(".scalar-result-value").inner_text() == "64 GiB"
        assert scalar_item.locator(".scalar-result-value").evaluate(
            "element => getComputedStyle(element).textAlign"
        ) == "left"

        memory_item = page.locator('details.item[data-item-id="browser.memory"]')
        assert memory_item.locator("thead th").all_inner_texts() == ["Metric", "Value"]
        assert memory_item.locator("tbody tr").inner_text().splitlines() == [
            "MemTotal",
            "64 GiB",
        ]
        browser.close()
