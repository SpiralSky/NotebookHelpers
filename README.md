### Description
Provides 2 main features:
- `%%load_clean`: A magic command that loads and run imports, optionally providing helpful info in cell bodies
- `load-clean-build`: A command which takes in some arguments to build notebooks (removes %%load_clean references and inlines cells). By default it uses /notebook and /build for notebook and build directories respectively

### NOTE:
For personal use. Feel free to fork and make this an actual python package, im not doing so since there are probably a lot of bugs with this.
I suggest just making it from scratch though
