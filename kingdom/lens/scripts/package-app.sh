#!/bin/zsh

set -euo pipefail

package_root="${0:A:h:h}"
build_directory="${package_root}/.build"
bundle_directory="${build_directory}/app"
app_path="${bundle_directory}/KINGDOM Lens.app"
stage_root=""

if [[ "${app_path}" != "${package_root}/.build/app/KINGDOM Lens.app" ]]; then
  print -u2 "Refusing an unexpected bundle path: ${app_path}"
  exit 1
fi

require_owned_directory() {
  local directory="$1"
  local owner

  if [[ ! -d "${directory}" || -L "${directory}" ]]; then
    print -u2 "Refusing a missing, non-directory, or linked path: ${directory}"
    exit 1
  fi
  if [[ "${directory:A}" != "${directory}" ]]; then
    print -u2 "Refusing a non-canonical directory: ${directory}"
    exit 1
  fi
  owner=$(/usr/bin/stat -f '%u' "${directory}")
  if [[ "${owner}" != "${EUID}" ]]; then
    print -u2 "Refusing a directory not owned by the current user: ${directory}"
    exit 1
  fi
}

cleanup_stage() {
  if [[ -n "${stage_root}" \
      && -d "${stage_root}" \
      && ! -L "${stage_root}" \
      && "${stage_root:h}" == "${bundle_directory}" \
      && "${stage_root:t}" == stage.* ]]; then
    /bin/rm -rf -- "${stage_root}"
  fi
}
trap cleanup_stage EXIT

require_owned_directory "${package_root}"
if [[ -e "${build_directory}" || -L "${build_directory}" ]]; then
  require_owned_directory "${build_directory}"
else
  /bin/mkdir "${build_directory}"
  require_owned_directory "${build_directory}"
fi

/usr/bin/swift build \
  --package-path "${package_root}" \
  --configuration release \
  --product KingdomLens \
  --manifest-cache local \
  --disable-dependency-cache \
  --disable-automatic-resolution

binary_root=$(/usr/bin/swift build \
  --package-path "${package_root}" \
  --configuration release \
  --show-bin-path \
  --manifest-cache local \
  --disable-dependency-cache \
  --disable-automatic-resolution)
binary_path="${binary_root}/KingdomLens"

if [[ ! -x "${binary_path}" ]]; then
  print -u2 "Release binary was not produced at ${binary_path}"
  exit 1
fi

require_owned_directory "${build_directory}"
if [[ -e "${bundle_directory}" || -L "${bundle_directory}" ]]; then
  require_owned_directory "${bundle_directory}"
else
  /bin/mkdir "${bundle_directory}"
  require_owned_directory "${bundle_directory}"
fi

stage_root=$(/usr/bin/mktemp -d "${bundle_directory}/stage.XXXXXX")
require_owned_directory "${stage_root}"
stage_app="${stage_root}/KINGDOM Lens.app"
contents_path="${stage_app}/Contents"

/bin/mkdir -p "${contents_path}/MacOS" "${contents_path}/Resources"
/bin/cp "${binary_path}" "${contents_path}/MacOS/KingdomLens"
/bin/cp "${package_root}/Resources/Info.plist" "${contents_path}/Info.plist"
/bin/chmod 755 "${contents_path}/MacOS/KingdomLens"

/usr/bin/plutil -lint "${contents_path}/Info.plist"
/usr/bin/codesign --force --sign - --timestamp=none "${stage_app}"
/usr/bin/codesign --verify --deep --strict --verbose=2 "${stage_app}"

if [[ -e "${app_path}" || -L "${app_path}" ]]; then
  require_owned_directory "${app_path}"
  existing_identifier=$(
    /usr/bin/plutil -extract CFBundleIdentifier raw -o - \
      "${app_path}/Contents/Info.plist" 2>/dev/null || true
  )
  if [[ "${existing_identifier}" != "love.chillspace.kingdom-lens" ]]; then
    print -u2 "Refusing to replace an app without the KINGDOM Lens identifier."
    exit 1
  fi
  /bin/rm -rf -- "${app_path}"
fi

/bin/mv "${stage_app}" "${app_path}"
/bin/rmdir "${stage_root}"
stage_root=""
/usr/bin/codesign --verify --deep --strict --verbose=2 "${app_path}"

print "${app_path}"
