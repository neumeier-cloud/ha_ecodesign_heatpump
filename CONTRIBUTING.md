# Contributing

Thanks for contributing to **EcoDesign Heat Pumps (Modbus)**!

## Development setup
1. Clone this repository.
2. Create a Home Assistant dev environment (core or container).
3. Symlink or copy `custom_components/ecodesign_waermepumpen` into your HA `config/custom_components/`.
4. Enable debug logging in `configuration.yaml`:
   ```yaml
   logger:
     default: warning
     logs:
       custom_components.ecodesign_waermepumpen: debug
       pymodbus: info
   ```

## Coding standards
- Follow Home Assistant integration guidelines.
- Keep `manifest.json` tidy, pin minimal working `pymodbus` range.
- Keep I/O in the hub/coordinator; entities should be thin.
- Use type hints and `async`/await patterns.

## Pull requests
- One feature/fix per PR.
- Include test/validation notes or manual verification steps.
- Update `CHANGELOG.md` under the **Unreleased** section or bump the version if appropriate.

## Register profiles
If your device firmware differs, please propose changes to the JSON profile under `profiles/`.
Document any deltas and include references (e.g., manual pages).

## Releasing
- Bump `"version"` in `manifest.json`.
- Update `CHANGELOG.md`.
- Create a Git tag: `vX.Y.Z`.
