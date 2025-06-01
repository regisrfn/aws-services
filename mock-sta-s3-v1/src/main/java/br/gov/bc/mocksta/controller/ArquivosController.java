package br.gov.bc.mocksta.controller;

import br.gov.bc.mocksta.model.FileInfo;
import br.gov.bc.mocksta.model.RangeInterval;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.model.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.*;
import org.springframework.util.StreamUtils;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import javax.servlet.http.HttpServletRequest;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Controlador que simula as rotas do STA do Banco Central:
 *  - POST   /staws/arquivos
 *  - PUT    /staws/arquivos/{protocolo}/conteudo
 *  - GET    /staws/arquivos/{protocolo}/posicaoupload
 *  - GET    /staws/arquivos/{protocolo}/conteudo
 *  - GET    /staws/arquivos?tipoConsulta=... (consulta de protocolos)
 *
 * Agora com integração ao AWS SDK v1 (AmazonS3), Basic Auth, fluxo de streaming
 * para download completo (sem carregar tudo na memória).
 */
@RestController
@RequestMapping("/staws/arquivos")
public class ArquivosController {

    // Mapa em memória: protocolo -> FileInfo (upload em andamento)
    private final Map<String, FileInfo> protocolosMap = new ConcurrentHashMap<>();

    // Gerador de IDs sequenciais para novos protocolos
    private final AtomicLong protocoloGenerator = new AtomicLong(1000);

    private final AmazonS3 s3Client;
    private final String bucketName;

    // Usuário e senha esperados para Basic Auth (somente mock)
    private static final String AUTH_USER = "usuarioteste";
    private static final String AUTH_PASS = "senhateste";

    @Autowired
    public ArquivosController(AmazonS3 s3Client, String bucketName) {
        this.s3Client = s3Client;
        this.bucketName = bucketName;
    }

    /**
     * Valida credenciais Basic Auth.
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

    /**
     * 1) POST /staws/arquivos
     * Gera um novo protocolo e cria o FileInfo com arquivo temporário local.
     * Retorna XML com <Protocolo> e <atom:link href=".../{protocolo}/conteudo" .../>.
     */
    @PostMapping(
            consumes = MediaType.APPLICATION_XML_VALUE,
            produces = MediaType.APPLICATION_XML_VALUE
    )
    public ResponseEntity<String> criarProtocolo(@RequestBody byte[] xmlBytes,
                                                 HttpServletRequest request) {
        // Basic Auth
        if (!isAuthorized(request)) {
            HttpHeaders headers = new HttpHeaders();
            headers.add("WWW-Authenticate", "Basic realm=\"STA Mock\"");
            return new ResponseEntity<>(headers, HttpStatus.UNAUTHORIZED);
        }

        // Gera um novo ID de protocolo
        String novoProtocolo = String.valueOf(protocoloGenerator.getAndIncrement());

        // Cria o FileInfo (arquivo temporário vazio) e guarda no mapa
        try {
            FileInfo fi = new FileInfo(novoProtocolo);
            protocolosMap.put(novoProtocolo, fi);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "Erro criando arquivo temporário para protocolo " + novoProtocolo);
        }

        // Monta o XML de resposta
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
     * 2) PUT /staws/arquivos/{protocolo}/conteudo
     * Se Content-Range ausente   -> grava tudo (upload completo).
     * Se Content-Range presente -> grava fragmento (upload em partes).
     * Se, após gravação, o FileInfo indicar que o upload está completo,
     * dispara o upload desse arquivo temporário ao S3 e limpa o arquivo local.
     */
    @PutMapping(
            path = "/{protocolo}/conteudo",
            consumes = MediaType.APPLICATION_OCTET_STREAM_VALUE
    )
    public ResponseEntity<Void> uploadConteudo(
            @PathVariable("protocolo") String protocolo,
            @RequestHeader(value = "Content-Range", required = false) String contentRange,
            @RequestBody byte[] bodyBytes,
            HttpServletRequest request
    ) {
        // Basic Auth
        if (!isAuthorized(request)) {
            HttpHeaders headers = new HttpHeaders();
            headers.add("WWW-Authenticate", "Basic realm=\"STA Mock\"");
            return new ResponseEntity<>(headers, HttpStatus.UNAUTHORIZED);
        }

        FileInfo fi = protocolosMap.get(protocolo);
        if (fi == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }

        try {
            if (contentRange == null) {
                // Upload completo: grava tudo de uma vez
                fi.writeFull(bodyBytes);
            } else {
                // Exemplo de Content-Range: "bytes 0-49999/200000"
                String cep = contentRange.trim();
                if (!cep.startsWith("bytes")) {
                    return ResponseEntity.status(HttpStatus.BAD_REQUEST).build();
                }
                // Remove "bytes " e separa em {inicio}, {fim}, {tamanhoTotal}
                String semBytes = cep.substring(6).trim();
                String[] partes = semBytes.split("[\\-/]");
                long inicio = Long.parseLong(partes[0]);
                long fim = Long.parseLong(partes[1]);
                long tamanhoTotal = Long.parseLong(partes[2]);

                if (fi.getTotalSize() < 0) {
                    fi.setTotalSize(tamanhoTotal);
                }
                fi.writeChunk(inicio, bodyBytes);
            }

            // Se, agora, o FileInfo indicar upload concluído, envie ao S3
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
     * Faz o upload do arquivo local (que já está 100% completo) para o S3.
     * Usa a chave “{protocolo}” (string) como objeto no bucket.
     */
    private void uploadFileToS3(FileInfo fi) {
        String key = fi.getProtocolo();
        File local = fi.getTempFile();

        try {
            PutObjectRequest por = new PutObjectRequest(bucketName, key, local);
            s3Client.putObject(por);
        } catch (AmazonS3Exception e) {
            // Se der erro aqui, apenas logamos e seguimos
            e.printStackTrace();
        }
    }

    /**
     * 3) GET /staws/arquivos/{protocolo}/posicaoupload
     * Retorna em XML os intervalos de bytes já recebidos para aquele protocolo.
     * Se o arquivo já estiver no S3, retorna [0, tamanho-1].
     */
    @GetMapping(
            path = "/{protocolo}/posicaoupload",
            produces = MediaType.APPLICATION_XML_VALUE
    )
    public ResponseEntity<String> getPosicaoUpload(
            @PathVariable("protocolo") String protocolo,
            HttpServletRequest request
    ) {
        // Basic Auth
        if (!isAuthorized(request)) {
            HttpHeaders headers = new HttpHeaders();
            headers.add("WWW-Authenticate", "Basic realm=\"STA Mock\"");
            return new ResponseEntity<>(headers, HttpStatus.UNAUTHORIZED);
        }

        // Primeiro verifique se já existe no S3
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

                return ResponseEntity.ok()
                        .contentType(MediaType.APPLICATION_XML)
                        .body(sbOk.toString());
            } catch (AmazonServiceException e) {
                return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
            }
        }

        // Se não estiver no S3, verifica se há FileInfo em memória (upload em andamento)
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
     * 4) GET /staws/arquivos/{protocolo}/conteudo
     * - Se existir no S3:
     *     • sem Range       → devolve tudo (200 OK), em streaming
     *     • com Range       → devolve trecho (206 Partial Content), em streaming
     * - Se não existir no S3, mas houver upload em andamento:
     *     • sem Range       → devolve local (200 OK), em streaming
     *     • com Range       → devolve trecho local (206 Partial Content), em byte[]
     *       (como trecho é menor, lemos em memória; mas em produção poderia fazer streaming parcial também).
     */
    @GetMapping(path = "/{protocolo}/conteudo")
    public ResponseEntity<?> downloadConteudo(
            @PathVariable("protocolo") String protocolo,
            @RequestHeader(value = "Range", required = false) String rangeHeader,
            HttpServletRequest request
    ) {
        // Basic Auth
        if (!isAuthorized(request)) {
            HttpHeaders headers = new HttpHeaders();
            headers.add("WWW-Authenticate", "Basic realm=\"STA Mock\"");
            return new ResponseEntity<>(headers, HttpStatus.UNAUTHORIZED);
        }

        // Se existir no S3, serve de lá (streaming)
        if (objectExistsInS3(protocolo)) {
            return serveFromS3Streaming(protocolo, rangeHeader);
        }

        // Senão, verifica upload em andamento local
        FileInfo fi = protocolosMap.get(protocolo);
        if (fi == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }

        try {
            if (rangeHeader != null && rangeHeader.startsWith("bytes=")) {
                // Leitura de um trecho específico do arquivo local
                long totalSize = fi.getTotalSize();
                if (totalSize < 0) {
                    return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
                }

                String semBytes = rangeHeader.substring(6).trim();
                String[] partes = semBytes.split("-");
                long inicio = Long.parseLong(partes[0]);
                long fim = partes.length > 1 ? Long.parseLong(partes[1]) : totalSize - 1;

                if (inicio < 0 || fim >= totalSize || inicio > fim) {
                    return ResponseEntity.status(HttpStatus.REQUESTED_RANGE_NOT_SATISFIABLE).build();
                }

                byte[] dados = fi.readRange(inicio, fim);
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
                headers.setContentLength(dados.length);
                headers.add(HttpHeaders.CONTENT_RANGE, "bytes " + inicio + "-" + fim + "/" + totalSize);
                return new ResponseEntity<>(dados, headers, HttpStatus.PARTIAL_CONTENT);
            } else {
                // Streaming completo do arquivo local (upload em andamento)
                long totalSize = fi.getTotalSize();
                if (totalSize < 0) {
                    return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
                }

                File localFile = fi.getTempFile();
                InputStreamResource resource = new InputStreamResource(new FileInputStream(localFile));

                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
                headers.setContentLength(localFile.length());
                return new ResponseEntity<>(resource, headers, HttpStatus.OK);
            }
        } catch (IOException e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    /**
     * 4.a) Serve o objeto diretamente do S3 (streaming).
     * - Sem Range: retorna 200 OK com InputStreamResource.
     * - Com Range: retorna 206 Partial Content com InputStreamResource.
     */
    private ResponseEntity<?> serveFromS3Streaming(String protocolo, String rangeHeader) {
        try {
            // Obtém metadados para saber o tamanho total
            ObjectMetadata metadata = s3Client.getObjectMetadata(bucketName, protocolo);
            long totalSize = metadata.getContentLength();

            if (rangeHeader != null && rangeHeader.startsWith("bytes=")) {
                // Download parcial (streaming do trecho)
                String semBytes = rangeHeader.substring(6).trim();
                String[] partes = semBytes.split("-");
                long inicio = Long.parseLong(partes[0]);
                long fim = partes.length > 1 ? Long.parseLong(partes[1]) : totalSize - 1;

                if (inicio < 0 || fim >= totalSize || inicio > fim) {
                    return ResponseEntity.status(HttpStatus.REQUESTED_RANGE_NOT_SATISFIABLE).build();
                }

                GetObjectRequest gor = new GetObjectRequest(bucketName, protocolo)
                        .withRange(inicio, fim);
                S3Object s3obj = s3Client.getObject(gor);
                InputStreamResource resource = new InputStreamResource(s3obj.getObjectContent());

                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
                headers.setContentLength(fim - inicio + 1);
                headers.add(HttpHeaders.CONTENT_RANGE, "bytes " + inicio + "-" + fim + "/" + totalSize);
                return new ResponseEntity<>(resource, headers, HttpStatus.PARTIAL_CONTENT);
            } else {
                // Download completo (streaming de todo o objeto)
                S3Object s3obj = s3Client.getObject(bucketName, protocolo);
                InputStreamResource resource = new InputStreamResource(s3obj.getObjectContent());

                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
                headers.setContentLength(totalSize);
                return new ResponseEntity<>(resource, headers, HttpStatus.OK);
            }
        } catch (AmazonS3Exception e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
    }

    /**
     * 5) GET /staws/arquivos?tipoConsulta=...&nivelDetalhe=...&dataHoraInicio=...&dataHoraFim=...
     * Rota para consulta de protocolos via parâmetros.
     * Retorna um XML com a lista de protocolos que atenderem aos filtros.
     */
    @GetMapping(produces = MediaType.APPLICATION_XML_VALUE)
    public ResponseEntity<String> consultaProtocolos(
            @RequestParam("tipoConsulta") String tipoConsulta,
            @RequestParam("nivelDetalhe") String nivelDetalhe,
            @RequestParam(value = "dataHoraInicio", required = false) String dataHoraInicio,
            @RequestParam(value = "dataHoraFim", required = false) String dataHoraFim,
            HttpServletRequest request
    ) {
        // Basic Auth
        if (!isAuthorized(request)) {
            HttpHeaders headers = new HttpHeaders();
            headers.add("WWW-Authenticate", "Basic realm=\"STA Mock\"");
            return new ResponseEntity<>(headers, HttpStatus.UNAUTHORIZED);
        }

        // Exemplo simplificado: retornamos todos os protocolos já gerados
        // num XML fictício. Em produção, usaria banco ou outro repositório.
        List<String> todosProtocolos = new ArrayList<>();
        todosProtocolos.addAll(s3Client.listObjects(bucketName).getObjectSummaries().stream()
                .map(S3ObjectSummary::getKey).toList());
        todosProtocolos.addAll(protocolosMap.keySet());

        // Monta XML de resposta conforme nível de detalhe
        StringBuilder sb = new StringBuilder();
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
        sb.append("<ResultadoConsulta tipoConsulta=\"").append(tipoConsulta)
          .append("\" nivelDetalhe=\"").append(nivelDetalhe).append("\">");

        DateTimeFormatter fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");
        String dhInicio = (dataHoraInicio != null) ? dataHoraInicio : "";
        String dhFim = (dataHoraFim != null) ? dataHoraFim : "";

        sb.append("<Parametros>");
        sb.append("<TipoConsulta>").append(tipoConsulta).append("</TipoConsulta>");
        sb.append("<NivelDetalhe>").append(nivelDetalhe).append("</NivelDetalhe>");
        if (!dhInicio.isEmpty()) {
            sb.append("<DataHoraInicio>").append(dhInicio).append("</DataHoraInicio>");
        }
        if (!dhFim.isEmpty()) {
            sb.append("<DataHoraFim>").append(dhFim).append("</DataHoraFim>");
        }
        sb.append("</Parametros>");

        sb.append("<Protocolos>");
        for (String protocoloKey : todosProtocolos) {
            sb.append("<Protocolo>");
            sb.append("<Numero>").append(protocoloKey).append("</Numero>");
            // DataHoraRegistro fictícia: agora
            sb.append("<DataHoraRegistro>")
              .append(LocalDateTime.now().format(fmt))
              .append("</DataHoraRegistro>");
            // Estado fictício
            sb.append("<Estado>CONCLUIDO</Estado>");
            sb.append("</Protocolo>");
        }
        sb.append("</Protocolos>");
        sb.append("</ResultadoConsulta>");

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_XML)
                .body(sb.toString());
    }

    /**
     * Verifica se existe um objeto com chave == protocolo no bucket S3.
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
     * Helper: constroi a URL base (scheme://host:port).
     */
    private String getBaseUrl(HttpServletRequest request) {
        String scheme = request.getScheme();
        String serverName = request.getServerName();
        int serverPort = request.getServerPort();
        return scheme + "://" + serverName + ":" + serverPort;
    }
}
