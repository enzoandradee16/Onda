# Remoção local de fundo

O portátil usa o Node.js já distribuído e somente os binários de CPU necessários
do ONNX Runtime 1.23.2. Não requer NumPy, PyTorch ou rembg.

Antes de montar um portátil novo, execute com o Python do compilador:

```powershell
python empacotamento/prepare_background_runtime.py --target "CAMINHO_DO_PORTATIL/_runtime/image-background-node"
```

O preparador verifica o SHA-512 dos arquivos oficiais, mantém os avisos de licença
e não executa scripts do npm. Os pacotes fixados estão em `background-runtime.json`.

O Android usa `onnxruntime-android:1.23.2`, restrito à ABI de cada APK.
O modelo U2NetP é baixado e verificado no primeiro uso, dentro dos dados do ONDA,
fora do cache descartável. As duas versões usam o mesmo pré-processamento e máscara.
