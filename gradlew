#!/usr/bin/env sh
set -eu

PINNED_GRADLE_VERSION='9.3.0'
PINNED_GRADLE_SHA256='0d585f69da091fc5b2beced877feab55a3064d43b8a1d46aeb07996b0915e0e0'
GRADLE_VERSION="${GRADLE_VERSION:-$PINNED_GRADLE_VERSION}"
BASE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

if [ "$GRADLE_VERSION" != "$PINNED_GRADLE_VERSION" ]; then
    echo "Refusing Gradle $GRADLE_VERSION; only Gradle $PINNED_GRADLE_VERSION is allowed." >&2
    exit 1
fi

verify_gradle_version() {
    candidate="$1"
    if [ ! -x "$candidate" ]; then
        echo "Gradle executable is not executable: $candidate" >&2
        return 1
    fi

    version_output="$($candidate --version 2>&1)" || {
        echo "Could not run Gradle version check: $candidate --version" >&2
        return 1
    }
    first_line="$(printf '%s\n' "$version_output" | sed -n '/^Gradle /{p;q;}')"
    if [ "$first_line" != "Gradle $PINNED_GRADLE_VERSION" ]; then
        echo "Refusing unexpected Gradle version from $candidate: $first_line" >&2
        return 1
    fi
}

sha256_of() {
    file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$file" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$file" | awk '{print $1}'
    else
        echo "sha256sum or shasum is required to verify Gradle distribution integrity." >&2
        return 1
    fi
}

verify_gradle_zip() {
    zip_file="$1"
    actual_sha256="$(sha256_of "$zip_file")"
    if [ "$actual_sha256" != "$PINNED_GRADLE_SHA256" ]; then
        echo "Refusing Gradle ZIP with unexpected SHA-256: $zip_file" >&2
        echo "Expected: $PINNED_GRADLE_SHA256" >&2
        echo "Actual:   $actual_sha256" >&2
        return 1
    fi
}

if [ -n "${REALITY_GRADLE_HOME:-}" ] || [ -n "${GRADLE_HOME:-}" ]; then
    echo "Refusing an external Gradle home; use the verified launcher distribution cache." >&2
    exit 1
fi

DIST_DIR="$BASE_DIR/.gradle/wrapper/dists/gradle-$PINNED_GRADLE_VERSION-bin"
PINNED_GRADLE_HOME="$DIST_DIR/gradle-$PINNED_GRADLE_VERSION"
ZIP="$DIST_DIR/gradle-$PINNED_GRADLE_VERSION-bin.zip"
mkdir -p "$DIST_DIR"

if [ -f "$ZIP" ]; then
    # Never replace an existing ZIP before checking its checksum.
    verify_gradle_zip "$ZIP"
else
    if ! command -v curl >/dev/null 2>&1; then
        echo "No verified Gradle $PINNED_GRADLE_VERSION is available and curl is missing; refusing download." >&2
        exit 1
    fi
    DOWNLOAD="$ZIP.download.$$"
    trap 'rm -f "$DOWNLOAD"' EXIT HUP INT TERM
    curl --fail --show-error --location --proto '=https' --tlsv1.2 \
        --connect-timeout 15 --max-time 300 --retry 1 --retry-delay 1 --retry-max-time 60 \
        --output "$DOWNLOAD" \
        "https://services.gradle.org/distributions/gradle-$PINNED_GRADLE_VERSION-bin.zip"
    verify_gradle_zip "$DOWNLOAD"
    mv "$DOWNLOAD" "$ZIP"
    trap - EXIT HUP INT TERM
fi

if [ -x "$PINNED_GRADLE_HOME/bin/gradle" ]; then
    verify_gradle_version "$PINNED_GRADLE_HOME/bin/gradle"
else
    if [ -e "$PINNED_GRADLE_HOME" ]; then
        echo "Refusing to overwrite an existing incomplete Gradle directory: $PINNED_GRADLE_HOME" >&2
        exit 1
    fi
    EXTRACT_DIR="$DIST_DIR/.extract.$$"
    mkdir -p "$EXTRACT_DIR"
    unzip -q "$ZIP" -d "$EXTRACT_DIR"
    if [ ! -x "$EXTRACT_DIR/gradle-$PINNED_GRADLE_VERSION/bin/gradle" ]; then
        echo "Verified Gradle ZIP did not contain the expected Gradle home." >&2
        exit 1
    fi
    mv "$EXTRACT_DIR/gradle-$PINNED_GRADLE_VERSION" "$PINNED_GRADLE_HOME"
    rmdir "$EXTRACT_DIR" 2>/dev/null || true
    verify_gradle_version "$PINNED_GRADLE_HOME/bin/gradle"
fi

exec "$PINNED_GRADLE_HOME/bin/gradle" "$@"
