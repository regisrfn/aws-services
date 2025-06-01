# Mock STA Application with AWS S3 (Java 17, Spring Boot, AWS SDK v1)

Este diretório contém o código-fonte de uma aplicação mock que simula as rotas `/staws/arquivos` do Banco Central,
integrada com AWS S3. Além disso, fornece exemplos de simulação com `curl` e uma coleção para Insomnia.

## Estrutura do Projeto

- `pom.xml` - Definições do Maven com dependências Spring Boot e AWS SDK v1 S3.
- `src/main/java/br/gov/bc/mocksta/`
  - `MockStaApplication.java` - Classe principal do Spring Boot.
  - `config/S3Config.java` - Cria o bean `AmazonS3` usando propriedades do S3.
  - `controller/ArquivosController.java` - Controlador REST para endpoints do STA e integração com S3.
  - `model/RangeInterval.java` e `FileInfo.java` - Classes para gerenciamento de upload resumido.

- `src/main/resources/`
  - `application.properties` - Configurações do Spring Boot (porta, import de aws.properties).
  - `aws.properties` - Configurações do AWS (região, bucket, credenciais opcionais).

## Como Compilar e Rodar

1. **Pré-requisitos**:
   - JDK 17 instalado.
   - Maven 3.6+ instalado.
   - Bucket S3 criado (ex.: `meu-bucket-sta-mock` em `sa-east-1`).
   - Credenciais AWS configuradas (via `~/.aws/credentials`, variáveis de ambiente ou `aws.properties`).

2. **Configurar `aws.properties`**:
   ```properties
   aws.s3.region=sa-east-1
   aws.s3.bucket-name=meu-bucket-sta-mock
   # aws.access-key=SEU_ACCESS_KEY
   # aws.secret-key=SEU_SECRET_KEY
   ```

3. **Compilar com Maven**:
   ```bash
   mvn clean package
   ```

4. **Executar**:
   ```bash
   mvn spring-boot:run
   ```
   ou
   ```bash
   java -jar target/mock-sta-s3-v1-1.0.0.jar
   ```

A aplicação ficará rodando em `http://localhost:8080`.


## Autenticação

Esta aplicação requer **HTTP Basic Auth** em todas as rotas. As credenciais esperadas são (hardcoded):

- **Usuário:** `usuarioteste`
- **Senha:** `senhateste`

Para enviar as requisições, inclua o header:

```
Authorization: Basic <Base64(usuarioteste:senhateste)>
```

## Exemplos de `curl` com autenticação

### 1) Gerar um novo protocolo
```bash
curl -v -X POST http://localhost:8080/staws/arquivos \
     -H "Content-Type: application/XML" \
     -H "Authorization: Basic $(echo -n 'usuarioteste:senhateste' | base64)" \
     -d '<RequisicaoProtocolo><NomeArquivo>teste.txt</NomeArquivo><NomeOrigem>MinhaEmpresa</NomeOrigem></RequisicaoProtocolo>'
```

### 2) Upload completo (arquivo pequeno)
```bash
curl -v -X PUT http://localhost:8080/staws/arquivos/1000/conteudo \
     -H "Content-Type: application/octet-stream" \
     -H "Authorization: Basic $(echo -n 'usuarioteste:senhateste' | base64)" \
     --data-binary @/caminho/para/arquivo.txt
```

### 3) Verificar progresso (posicaoupload)
```bash
curl -v http://localhost:8080/staws/arquivos/1000/posicaoupload \
     -H "Authorization: Basic $(echo -n 'usuarioteste:senhateste' | base64)"
```

### 4) Download completo
```bash
curl -v http://localhost:8080/staws/arquivos/1000/conteudo \
     -H "Authorization: Basic $(echo -n 'usuarioteste:senhateste' | base64)" \
     --output baixado.txt
```

### 5) Download parcial (Range)
```bash
curl -v http://localhost:8080/staws/arquivos/1000/conteudo \
     -H "Authorization: Basic $(echo -n 'usuarioteste:senhateste' | base64)" \
     -H "Range: bytes=100-499" \
     --output trecho.txt
```

### 6) Upload em partes (multipart)
```bash
# Parte 1 (bytes 0-499 de um arquivo de 1000 bytes)
head -c 500 /caminho/para/arquivo_grande.bin > parte1.bin
curl -v -X PUT http://localhost:8080/staws/arquivos/1001/conteudo \
     -H "Content-Type: application/octet-stream" \
     -H "Authorization: Basic $(echo -n 'usuarioteste:senhateste' | base64)" \
     -H "Content-Range: bytes 0-499/1000" \
     --data-binary @parte1.bin

# Verificar progresso
curl -v http://localhost:8080/staws/arquivos/1001/posicaoupload \
     -H "Authorization: Basic $(echo -n 'usuarioteste:senhateste' | base64)"

# Parte 2 (bytes 500-999)
tail -c +501 /caminho/para/arquivo_grande.bin > parte2.bin
curl -v -X PUT http://localhost:8080/staws/arquivos/1001/conteudo \
     -H "Content-Type: application/octet-stream" \
     -H "Authorization: Basic $(echo -n 'usuarioteste:senhateste' | base64)" \
     -H "Content-Range: bytes 500-999/1000" \
     --data-binary @parte2.bin

# Verificar progresso final
curl -v http://localhost:8080/staws/arquivos/1001/posicaoupload \
     -H "Authorization: Basic $(echo -n 'usuarioteste:senhateste' | base64)"
```



### 1) Gerar um novo protocolo
```bash
curl -v -X POST http://localhost:8080/staws/arquivos      -H "Content-Type: application/XML"      -d '<RequisicaoProtocolo><NomeArquivo>teste.txt</NomeArquivo><NomeOrigem>MinhaEmpresa</NomeOrigem></RequisicaoProtocolo>'
```
Resposta:
```xml
<Resultado xmlns:atom="http://www.w3.org/2005/Atom">
  <Protocolo>1000</Protocolo>
  <atom:link href="http://localhost:8080/staws/arquivos/1000/conteudo" rel="conteudo" type="application/octet-stream"/>
</Resultado>
```

### 2) Upload completo (arquivo pequeno)
```bash
curl -v -X PUT http://localhost:8080/staws/arquivos/1000/conteudo      -H "Content-Type: application/octet-stream"      --data-binary @/caminho/para/arquivo.txt
```
Após isso, o arquivo será enviado ao S3 e removido do local.

### 3) Verificar progresso (posicaoupload)
```bash
curl -v http://localhost:8080/staws/arquivos/1000/posicaoupload
```
Resposta:
```xml
<PosicaoUpload>
  <Posicao><Inicio>0</Inicio><Fim>tamanho-1</Fim></Posicao>
</PosicaoUpload>
```

### 4) Download completo
```bash
curl -v http://localhost:8080/staws/arquivos/1000/conteudo --output baixado.txt
```

### 5) Download parcial (Range)
```bash
curl -v http://localhost:8080/staws/arquivos/1000/conteudo      -H "Range: bytes=100-499"      --output trecho.txt
```

### 6) Upload em partes (multipart)
```bash
# Parte 1 (bytes 0-499 de um arquivo de 1000 bytes)
head -c 500 /caminho/para/arquivo_grande.bin > parte1.bin
curl -v -X PUT http://localhost:8080/staws/arquivos/1001/conteudo      -H "Content-Type: application/octet-stream"      -H "Content-Range: bytes 0-499/1000"      --data-binary @parte1.bin

# Verificar progresso
curl -v http://localhost:8080/staws/arquivos/1001/posicaoupload

# Parte 2 (bytes 500-999)
tail -c +501 /caminho/para/arquivo_grande.bin > parte2.bin
curl -v -X PUT http://localhost:8080/staws/arquivos/1001/conteudo      -H "Content-Type: application/octet-stream"      -H "Content-Range: bytes 500-999/1000"      --data-binary @parte2.bin

# Verificar progresso final
curl -v http://localhost:8080/staws/arquivos/1001/posicaoupload
```

## Coleção Insomnia (JSON)

Dentro deste zip, há um arquivo `insomnia_collection.json` que pode ser importado no Insomnia.
