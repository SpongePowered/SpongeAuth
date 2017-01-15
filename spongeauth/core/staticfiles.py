from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class SourcemapManifestStaticFilesStorage(ManifestStaticFilesStorage):
    CSS_SOURCE_MAPS_PATTERN = (
        r"""(/\*#\s*sourceMappingURL=(.*)\s*\*/)""",
        """/*# sourceMappingURL=%s */"""
    )

    JS_SOURCE_MAPS_PATTERN = (
        r"""(//#\s*sourceMappingURL=(.*)$)""",
        """//# sourceMappingURL=%s"""
    )

    patterns = (
        ("*.css", (
            r"""(url\(['"]{0,1}\s*(.*?)["']{0,1}\))""",
            (r"""(@import\s*["']\s*(.*?)["'])""", """@import url("%s")"""),
            CSS_SOURCE_MAPS_PATTERN,
        )),
        ("*.js", (
            JS_SOURCE_MAPS_PATTERN,
        )),
    )
