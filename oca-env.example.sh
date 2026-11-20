# Toolchain for the Harness VP engine. Copy to oca-env.sh (git-ignored), set the
# paths to where you installed each dependency, and ./start.sh will source it.
# Versions follow tt-oca-harness-model's CI.
export SYSTEMC_HOME=/path/to/systemc-3.0.2        # built with -std=c++20
export CCI_HOME=/path/to/cci-1.0.2
export WHISPER_HOME=/path/to/whisper              # commit a53d0f3e, built -fPIC
export BOOST_ROOT=/usr                            # Boost >= 1.74 with iostreams + program_options
export BOOST_DIR=$BOOST_ROOT
export OPENSSL_ROOT=/usr                          # OpenSSL 3.x
export CMAKE_CXX_STANDARD=20
export RISCV_TOOLCHAIN_PATH=/path/to/xpack-riscv-none-elf-gcc-15.2.0-1   # needs RV32 + RV64
export RISCV_PREFIX=riscv-none-elf-
export GCC_PREFIX=riscv-none-elf
export PATH=$RISCV_TOOLCHAIN_PATH/bin:$PATH
export LD_LIBRARY_PATH=$SYSTEMC_HOME/lib-linux64:${LD_LIBRARY_PATH:-}

# Optional: where the model checkout and smu-vp binary are, if not under upstream/
# export OCA_MODEL_ROOT=/path/to/tt-oca-harness-model
# export OCA_SMU_VP=$OCA_MODEL_ROOT/vp/build_smc/bin/smu-vp
