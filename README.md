# Alice AI Assistant

Aims to implement a desktop LLM application running in low physical resource.

Base on:

[llama-cpp-python](https://github.com/abetlen/llama-cpp-python)

[faster-whipser](https://github.com/SYSTRAN/faster-whisper)

[MeloTTS](https://github.com/myshell-ai/MeloTTS)

PySide6 for application UI.

## Installation

Python 3.11

> A miniconda environment is advised.

1. pip install -r requirements.txt

    > Note: for better experience with llm, choose a backend of llama-cpp-python and install before requirements.txt.

    - cpu (Pre-built Wheel) 
        ```
        pip install llama-cpp-python \
        --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
        ```

    - OpenBLAS (CPU)
        ```
        CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python
        ```
    
    - CUDA
        ```
        CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python

        or Pre-built Wheel:
        CUDA Version is 12.1, 12.2, 12.3, 12.4 or 12.5

        pip install llama-cpp-python \
        --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/<cuda-version>
        ```
    
    - hipBLAS (ROCm)
        ```
        CMAKE_ARGS="-DGGML_HIPBLAS=on" pip install llama-cpp-python
        ```       
    
    > Note: if in Linux, make sure PySide6 version is the same with your system package. 
    Then use the following comand to enable fcitx.

    ```
    cp /usr/lib/qt6/plugins/platforminputcontexts/libfcitx5platforminputcontextplugin.so \
    [your miniconda dir]/env/[your env]/lib/python3.11/site-packages/PySide6/Qt/plugins/platforminputcontexts/
    ```

2. download local model and extract to project directory.

3. download offline data and extract to project directory.

4. copy [dicdir] to target directory.
    ```
    cp -r ./offline_data/dicdir \
    [your miniconda dir]/env/[your env]/lib/python3.11/site-packages/unidic/
    ```

5. then you can startup app in the terminal.

## Directory Tree

```
proj
    - core
    - ui
    - assets
    - model
    - driver (optional for Browser)
    - offline_data
```