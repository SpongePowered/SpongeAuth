from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class SourcemapManifestStaticFilesStorage(ManifestStaticFilesStorage):
    patterns = (
        ("*.css", (
            r"""(?P<matched>url\(['"]{0,1}\s*(?P<url>.*?)["']{0,1}\))""",
            (
                r"""(?P<matched>@import\s*["']\s*(?P<url>.*?)["'])""",
                """@import url("%(url)s")""",
            ),
            (
                r'(?m)(?P<matched>)^(/\*# (?-i:sourceMappingURL)=(?P<url>.*) \*/)$',
                '/*# sourceMappingURL=%(url)s */',
            ),
        )),
        ('*.js', (
            (
                '(?m)(?P<matched>)^(//# (?-i:sourceMappingURL)=(?P<url>.*))$',
                '//# sourceMappingURL=%(url)s',
            ),
        )),
    )
