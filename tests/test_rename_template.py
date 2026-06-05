from rename_template import replace_file_content

OLD = ("my_service_template", "mst", "my-service-template", "My Service Template")
NEW = ("my_service", "ms", "my-service", "My Service")


def test_replaces_dist_name() -> None:
    text = 'name = "my-service-template"'
    result = replace_file_content(text, *OLD, *NEW)
    assert result == 'name = "my-service"'


def test_replaces_console_script_before_import_path() -> None:
    text = 'mst = "my_service_template.cli:app"'
    result = replace_file_content(text, *OLD, *NEW)
    assert result == 'ms = "my_service.cli:app"'


def test_replaces_cli_in_readme_code_block() -> None:
    text = "uv run mst run\n"
    result = replace_file_content(text, *OLD, *NEW)
    assert result == "uv run ms run\n"


def test_replaces_env_var_prefix() -> None:
    text = "MST_LOG_LEVEL=DEBUG MST_RUN_SECONDS=0 uv run mst run\n"
    result = replace_file_content(text, *OLD, *NEW)
    assert "MST_" not in result
    assert "MS_" in result
