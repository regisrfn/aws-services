package br.gov.bc.mocksta.controller;

import br.gov.bc.mocksta.model.FileInfo;
import br.gov.bc.mocksta.model.RangeInterval;
import com.amazonaws.AmazonServiceException;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.model.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.*;
import org.springframework.util.StreamUtils;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import javax.servlet.http.HttpServletRequest;
import java.io.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Controlador que simula as rotas do STA do Banco Central:
 *  - POST   /staws/arquivos
 *  - PUT    /staws/arquivos/{protocolo}/conteudo
 *  - GET    /staws/arquivos/{protocolo}/posicaoupload
 *  - GET    /staws/arquivos/{protocolo}/conteudo
 *
 * Agora com integração ao AWS SDK v1 (AmazonS3).
 */
@RestController
@RequestMapping("/staws/arquivos")
public class ArquivosController {

import javax.servlet.http.HttpServletRequest;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

    // User and password for Basic Auth
    private static final String AUTH_USER = "usuarioteste";
    private static final String AUTH_PASS = "senhateste";

    /**
     * Validates the Basic Auth credentials from the request.
     */
    private boolean isAuthorized(HttpServletRequest request) {
        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Basic ")) {
            return false;
        }
        String base64Credentials = authHeader.substring("Basic ".length()).trim();
        byte[] decodedBytes = Base64.getDecoder().decode(base64Credentials);
        String credentials = new String(decodedBytes, StandardCharsets.UTF_8);
        String[] values = credentials.split(":", 2);
        if (values.length != 2) {
            return false;
        }
        String user = values[0];
        String pass = values[1];
        return AUTH_USER.equals(user) && AUTH_PASS.equals(pass);
    }

    // Mapa em memória: protocolo -> FileInfo (upload em andamento)
    private final Map<String, FileInfo> protocolosMap = new ConcurrentHashMap<>();

    // Gerador de IDs sequenciais para novos protocolos
    private final AtomicLong protocoloGenerator = new AtomicLong(1000);

    private final AmazonS3 s3Client;
    private final String bucketName;

    @Autowired
    public ArquivosController(AmazonS3 s3Client, String bucketName) {
        this.s3Client = s3Client;
        this.bucketName = bucketName;
    }

    /**
     * POST /staws/arquivos
     * Recebe XML com metadados (que, neste mock, não é parseado de verdade),
     * gera um novo protocolo, armazena um FileInfo (arquivo temporário) e retorna
     * o XML de resposta com <Protocolo> e <atom:link href=".../conteudo" .../>.
     */
    @PostMapping(
    // Basic Auth validation
    if (!isAuthorized(request)) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("WWW-Authenticate", "Basic realm=\"STA Mock\"");
        return new ResponseEntity<>(headers, HttpStatus.UNAUTHORIZED);
    }
            consumes = MediaType.APPLICATION_XML_VALUE,
            produces = MediaType.APPLICATION_XML_VALUE
    )
    public ResponseEntity<String> criarProtocolo(
            @RequestBody byte[] xmlBytes,
            HttpServletRequest request
    ) {
        // Gera novo protocolo
        String novoProtocolo = String.valueOf(protocoloGenerator.getAndIncrement());

        // Cria FileInfo para esse protocolo e guarda no mapa
        try {
            FileInfo fi = new FileInfo(novoProtocolo);
            protocolosMap.put(novoProtocolo, fi);
        } catch (IOException e) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "Erro ao criar arquivo temporário para protocolo " + novoProtocolo
            );
        }

        // Monta XML de resposta
        StringBuilder sb = new StringBuilder();
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
          .append("<Resultado xmlns:atom=\"http://www.w3.org/2005/Atom\">")
          .append("<Protocolo>").append(novoProtocolo).append("</Protocolo>")
          .append("<atom:link ")
            .append("href=\"").append(getBaseUrl(request))
                       .append("/staws/arquivos/").append(novoProtocolo).append("/conteudo\" ")
            .append("rel=\"conteudo\" type=\"application/octet-stream\"/>")
          .append("</Resultado>");

        return ResponseEntity
                .status(HttpStatus.OK)
                .contentType(MediaType.APPLICATION_XML)
                .body(sb.toString());
    }

    /**
     * PUT /staws/arquivos/{protocolo}/conteudo
     * - Se header "Content-Range" estiver ausente, trata como upload completo (writeFull).
     * - Se "Content-Range" presente, parseia e grava com writeChunk(inicio, dados).
     * Se após gravação o upload estiver completo (fi.isUploadComplete() == true),
     * envia o arquivo local ao S3 (putObject) e remove do mapa local (fi.cleanup()).
     */
    @PutMapping(
    // Basic Auth validation
    if (!isAuthorized(request)) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("WWW-Authenticate", "Basic realm=\"STA Mock\"");
        return new ResponseEntity<>(headers, HttpStatus.UNAUTHORIZED);
    }
            path = "/{protocolo}/conteudo",
            consumes = MediaType.APPLICATION_OCTET_STREAM_VALUE
    )
    public ResponseEntity<Void> uploadConteudo(
            @PathVariable("protocolo") String protocolo,
            @RequestHeader(value = "Content-Range", required = false) String contentRange,
            @RequestBody byte[] bodyBytes
    ) {
        FileInfo fi = protocolosMap.get(protocolo);
        if (fi == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }

        try {
            if (contentRange == null) {
                // Upload completo
                fi.writeFull(bodyBytes);
            } else {
                // Exemplo de Content-Range: "bytes 0-499/2000"
                String cep = contentRange.trim();
                if (!cep.startsWith("bytes")) {
                    return ResponseEntity.status(HttpStatus.BAD_REQUEST).build();
                }
                String semBytes = cep.substring(6).trim(); // remove "bytes "
                String[] partes = semBytes.split("[\\-/]");
                // partes = { inicio, fim, totalSize }
                long inicio = Long.parseLong(partes[0]);
                long fim = Long.parseLong(partes[1]);
                long tamanhoTotal = Long.parseLong(partes[2]);

                if (fi.getTotalSize() < 0) {
                    fi.setTotalSize(tamanhoTotal);
                }
                fi.writeChunk(inicio, bodyBytes);
            }

            // Se o upload estiver completo após essa gravação, enviamos para o S3
            if (fi.isUploadComplete()) {
                uploadFileToS3(fi);
                fi.cleanup();
                protocolosMap.remove(protocolo);
            }
        } catch (IOException e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }

        return ResponseEntity.ok().build();
    }

    /**
     * Envia o arquivo local (FileInfo.getTempFile()) para o S3 usando putObject.
     * A chave do objeto será igual ao número de protocolo (String).
     */
    private void uploadFileToS3(FileInfo fi) {
        String key = fi.getProtocolo();
        File local = fi.getTempFile();
        try {
            PutObjectRequest por = new PutObjectRequest(bucketName, key, local);
            s3Client.putObject(por);
        } catch (AmazonS3Exception e) {
            // Loga e segue; não lança para não interromper o fluxo principal
            e.printStackTrace();
        }
    }

    /**
     * GET /staws/arquivos/{protocolo}/posicaoupload
     * - Se o objeto já existe no S3 (headObject), retorna intervalo [0, tamanho-1] em XML.
     * - Caso contrário, se houver upload em andamento (fileInfo em memória), retorna todos os intervals recebidos.
     * - Se não houver nenhum dos dois, responde 404.
     */
    @GetMapping(
    // Basic Auth validation
    if (!isAuthorized(request)) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("WWW-Authenticate", "Basic realm=\"STA Mock\"");
        return new ResponseEntity<>(headers, HttpStatus.UNAUTHORIZED);
    }
            path = "/{protocolo}/posicaoupload",
            produces = MediaType.APPLICATION_XML_VALUE
    )
    public ResponseEntity<String> getPosicaoUpload(@PathVariable("protocolo") String protocolo) {
        // 1) Checa se já existe no S3
        if (objectExistsInS3(protocolo)) {
            try {
                ObjectMetadata metadata = s3Client.getObjectMetadata(bucketName, protocolo);
                long tamanhoTotal = metadata.getContentLength();

                StringBuilder sbOk = new StringBuilder();
                sbOk.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
                    .append("<PosicaoUpload>")
                    .append("<Posicao>")
                    .append("<Inicio>0</Inicio>")
                    .append("<Fim>").append(tamanhoTotal - 1).append("</Fim>")
                    .append("</Posicao>")
                    .append("</PosicaoUpload>");

                return ResponseEntity
                        .status(HttpStatus.OK)
                        .contentType(MediaType.APPLICATION_XML)
                        .body(sbOk.toString());
            } catch (AmazonS3Exception e) {
                // Se for erro 404 (NoSuchKey) ou outro erro, retornamos false
                return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
            }
        }

        // 2) Se não estiver no S3, verifica se há FileInfo em memória (upload em andamento)
        FileInfo fi = protocolosMap.get(protocolo);
        if (fi == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }

        List<RangeInterval> ranges = fi.getReceivedRanges();
        StringBuilder sb = new StringBuilder();
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
          .append("<PosicaoUpload>");
        for (RangeInterval intervalo : ranges) {
            sb.append("<Posicao>")
              .append("<Inicio>").append(intervalo.getInicio()).append("</Inicio>")
              .append("<Fim>").append(intervalo.getFim()).append("</Fim>")
              .append("</Posicao>");
        }
        sb.append("</PosicaoUpload>");

        return ResponseEntity
                .status(HttpStatus.OK)
                .contentType(MediaType.APPLICATION_XML)
                .body(sb.toString());
    }

    /**
     * GET /staws/arquivos/{protocolo}/conteudo
     * - Se o objeto existir no S3:
     *     • sem Range           → GET completo do S3 e devolve 200 OK.
     *     • com Range           → GET do S3 com Range e devolve 206 Partial Content.
     * - Se o objeto não existir no S3, mas houver FileInfo em memória:
     *     • sem Range           → devolve tudo que já está gravado localmente (200 OK).
     *     • com Range           → devolve apenas o trecho solicitado do local (206 Partial Content).
     * - Se não houver nem S3 nem FileInfo, devolve 404.
     */
    @GetMapping(path = "/{protocolo}/conteudo")
    // Basic Auth validation
    if (!isAuthorized(request)) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("WWW-Authenticate", "Basic realm=\"STA Mock\"");
        return new ResponseEntity<>(headers, HttpStatus.UNAUTHORIZED);
    }
    public ResponseEntity<byte[]> downloadConteudo(
            @PathVariable("protocolo") String protocolo,
            @RequestHeader(value = "Range", required = false) String rangeHeader
    ) {
        // 1) Se existir no S3, serve de lá
        if (objectExistsInS3(protocolo)) {
            return serveFromS3(protocolo, rangeHeader);
        }

        // 2) Senão, vê se há upload em andamento
        FileInfo fi = protocolosMap.get(protocolo);
        if (fi == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }

        try {
            if (rangeHeader != null && rangeHeader.startsWith("bytes=")) {
                // Tratamento de Range local
                String semBytes = rangeHeader.substring(6).trim();
                String[] partes = semBytes.split("-");
                long inicio = Long.parseLong(partes[0]);
                long fim = partes.length > 1 
                           ? Long.parseLong(partes[1]) 
                           : fi.getTotalSize() - 1;

                if (fi.getTotalSize() < 0) {
                    return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
                }
                if (inicio < 0 || fim >= fi.getTotalSize() || inicio > fim) {
                    return ResponseEntity.status(HttpStatus.REQUESTED_RANGE_NOT_SATISFIABLE).build();
                }

                byte[] dados = fi.readRange(inicio, fim);
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
                headers.setContentLength(dados.length);
                headers.add(HttpHeaders.CONTENT_RANGE, 
                            "bytes " + inicio + "-" + fim + "/" + fi.getTotalSize());
                return new ResponseEntity<>(dados, headers, HttpStatus.PARTIAL_CONTENT);
            } else {
                // Sem Range: devolve tudo já gravado localmente
                if (fi.getTotalSize() < 0) {
                    return ResponseEntity.status(HttpStatus.NOT_FOUND).build();}
                byte[] dados = fi.readFull();
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
                headers.setContentLength(dados.length);
                return new ResponseEntity<>(dados, headers, HttpStatus.OK);
            }
        } catch (IOException e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    /**
     * Verifica se existe um objeto com chave == protocolo no bucket S3.
     * Faz getObjectMetadata: se não lançar exceção, retorna true; se lançar
     * AmazonS3Exception indicando 404, retorna false.
     */
    private boolean objectExistsInS3(String protocolo) {
        try {
            s3Client.getObjectMetadata(bucketName, protocolo);
            return true;
        } catch (AmazonS3Exception e) {
            if (e.getStatusCode() == 404) {
                return false;
            }
            return false;
        }
    }

    /**
     * Serve o objeto diretamente do S3.
     * - Sem Range: retorna 200 OK com todo o objeto.
     * - Com Range: usa GetObjectRequest com Range e retorna 206 Partial Content.
     */
    private ResponseEntity<byte[]> serveFromS3(String protocolo, String rangeHeader) {
        try {
            ObjectMetadata metadata = s3Client.getObjectMetadata(bucketName, protocolo);
            long totalSize = metadata.getContentLength();

            if (rangeHeader != null && rangeHeader.startsWith("bytes=")) {
                String semBytes = rangeHeader.substring(6).trim();
                String[] partes = semBytes.split("-");
                long inicio = Long.parseLong(partes[0]);
                long fim = partes.length > 1 
                           ? Long.parseLong(partes[1]) 
                           : totalSize - 1;

                if (inicio < 0 || fim >= totalSize || inicio > fim) {
                    return ResponseEntity.status(HttpStatus.REQUESTED_RANGE_NOT_SATISFIABLE).build();
                }

                GetObjectRequest gor = new GetObjectRequest(bucketName, protocolo)
                        .withRange(inicio, fim);
                S3Object s3obj = s3Client.getObject(gor);
                try (S3ObjectInputStream s3is = s3obj.getObjectContent()) {
                    byte[] dados = StreamUtils.copyToByteArray(s3is);
                    HttpHeaders headers = new HttpHeaders();
                    headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
                    headers.setContentLength(dados.length);
                    headers.add(HttpHeaders.CONTENT_RANGE,
                            "bytes " + inicio + "-" + fim + "/" + totalSize);
                    return new ResponseEntity<>(dados, headers, HttpStatus.PARTIAL_CONTENT);
                }
            } else {
                S3Object s3obj = s3Client.getObject(bucketName, protocolo);
                try (S3ObjectInputStream s3is = s3obj.getObjectContent()) {
                    byte[] dados = StreamUtils.copyToByteArray(s3is);
                    HttpHeaders headers = new HttpHeaders();
                    headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
                    headers.setContentLength(dados.length);
                    return new ResponseEntity<>(dados, headers, HttpStatus.OK);
                }
            }
        } catch (AmazonS3Exception e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        } catch (IOException e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    /**
     * Monta a URL base no formato "http://host:porta", para incluir no <atom:link> do POST.
     */
    private String getBaseUrl(HttpServletRequest request) {
        String scheme = request.getScheme();       // http ou https
        String serverName = request.getServerName(); // localhost ou host real
        int serverPort = request.getServerPort();  // ex.: 8080
        return scheme + "://" + serverName + ":" + serverPort;
    }
}
