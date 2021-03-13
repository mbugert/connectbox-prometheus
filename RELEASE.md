# Release Checklist
- [ ] Testing
- [ ] Update version and info in `setup.py`
- [ ] Build
    ```
    python -m build
    ```
- [ ] Test pypi release
    ```
    python -m twine upload --repository testpypi dist/*
    ```
- [ ] Try installing that
    ```
    python3 -m venv tmpvenv
    source tmpvenv/bin/activate
    pip install -i https://test.pypi.org/simple/ --no-deps PACKAGE_NAME
    deactivate
    rm -rf tmpvenv
    ```
- [ ] Commit, merge into `master` with PR
- [ ] Proper pypi release
    ```
    twine upload dist/*
    ```
- [ ] Release on github with appropriate tag

## Wishlist
Automate this with https://github.com/pypa/gh-action-pypi-publish