# Install

The composer runs with only Python. The Harness virtual platform is optional: it needs Linux and a SystemC toolchain, and adds the firmware-level runs.

## Run the composer

You need Python 3.10 or later and a recent browser.

```bash
git clone https://github.com/kadomoto/oca-chiplet-composer
cd oca-chiplet-composer
pip install -r backend/requirements.txt
./start.sh
```

Open <http://127.0.0.1:8765>. The example design, five chiplets on an organic package, loads on first start. **File → Load example design** brings it back.

Everything except the **Harness VP** checkbox works now. The sidebar shows `smu-vp: Not built` until you add the virtual platform.

!!! tip "Another port"
    `PORT=9000 ./start.sh` serves on port 9000 instead. The server listens on `127.0.0.1` only.

## Add the Harness virtual platform

### 1. Get the model

The composer needs two changes to tt-oca-harness-model. Both are on the `feat/mdie-vp` branch of [kadomoto/tt-oca-harness-model](https://github.com/kadomoto/tt-oca-harness-model/tree/feat/mdie-vp):

- the `[double]` INI fix ([tenstorrent/tt-oca-harness-model#284](https://github.com/tenstorrent/tt-oca-harness-model/pull/284)); without it, `smu-vp` silently ignores the link delay the composer injects;
- `mdie-vp`, a platform with two dies whose AoUs are connected, and a window for chiplet logic.

```bash
mkdir -p upstream && cd upstream
git clone https://github.com/tenstorrent/tt-oca-harness-model
cd tt-oca-harness-model
git fetch https://github.com/kadomoto/tt-oca-harness-model feat/mdie-vp
git checkout FETCH_HEAD
git submodule update --init --recursive
```

### 2. Install the toolchain

These are the versions tt-oca-harness-model's CI uses. The model's [README](https://github.com/tenstorrent/tt-oca-harness-model#building-the-sep-vp) has the build steps for each.

| Dependency | Version | Note |
|---|---|---|
| SystemC | 3.0.2 | built with `-std=c++20` |
| CCI | 1.0.2 | |
| Boost | 1.74 or later | needs `iostreams` and `program_options` |
| OpenSSL | 3.x | |
| [Whisper](https://github.com/tenstorrent/whisper) | commit `a53d0f3e` | built with `-fPIC` |
| RISC-V GCC | xPack 15.2.0-1 | needs both RV32 (SEP) and RV64 (SMC) multilibs |

### 3. Point the composer at it

```bash
cp oca-env.example.sh oca-env.sh   # then fill in your paths
```

`oca-env.sh` sets `SYSTEMC_HOME`, `CCI_HOME`, `WHISPER_HOME`, `BOOST_ROOT`, the RISC-V toolchain and, if the model is not under `upstream/`, `OCA_MODEL_ROOT`. `./start.sh` sources it; it also reads the file named by `OCA_ENV`.

### 4. Build the platforms

```bash
source oca-env.sh
cd upstream/tt-oca-harness-model
cmake -S vp -B vp/build_smc -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=20 -DSMC_CXX_STANDARD=20
cmake --build vp/build_smc --target smu-vp mdie-vp -j
```

### 5. Check

Restart `./start.sh`. The sidebar's **Harness VP** section should read `smu-vp: Ready` and `mdie-vp: Ready (two dies)`. In the model repository, `sw/smu-vp-tests/run_smu_vp_tests.sh` should report all tests passing.

If something is missing, see [Troubleshooting](../troubleshooting.md).
