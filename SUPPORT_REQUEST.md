# GitHub Support request: purge a cached personal screenshot

Repository: <https://github.com/piyush97/focuslog>

- Sanitized branch head: `acd39f330d88f088b637f4868f77fc1aadbd398a`
- Former commit: `83390711f02d5ea721b1a0c1a2972c52892d6293`
- Affected path: `docs/image.png`
- Still-accessible raw URL: <https://raw.githubusercontent.com/piyush97/focuslog/83390711f02d5ea721b1a0c1a2972c52892d6293/docs/image.png>

The repository history was rewritten; this image and the accidental bytecode are absent from every reachable commit. The former commit page and GitHub API return 404. However, anonymous HEAD and GET requests to the raw-content URL above still return 200 and the original 363,840-byte image (`X-Cache: HIT`). The screenshot exposes personal browser/window activity and should not be publicly accessible.

Please purge the cached raw file and any cached commit/tree view associated with this former commit/path. The replacement dashboard preview uses fictional demo activity. I will verify by requesting the exact raw URL and confirming it returns 404.
