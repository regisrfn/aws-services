package br.gov.bc.mocksta.config;

import com.amazonaws.auth.AWSCredentials;
import com.amazonaws.auth.AWSStaticCredentialsProvider;
import com.amazonaws.auth.BasicAWSCredentials;
import com.amazonaws.auth.DefaultAWSCredentialsProviderChain;
import com.amazonaws.regions.Regions;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3ClientBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Configuração do AmazonS3 usando AWS SDK v1 (aws-java-sdk-s3).
 * Lê região e bucket via aws.properties, e opcionalmente credenciais estáticas.
 */
@Configuration
public class S3Config {

    @Value("${aws.s3.region}")
    private String awsRegion;

    @Value("${aws.s3.bucket-name}")
    private String bucketName;

    // Propriedades opcionais para credenciais estáticas
    @Value("${aws.access-key:#{null}}")
    private String accessKey;

    @Value("${aws.secret-key:#{null}}")
    private String secretKey;

    /**
     * Bean do AmazonS3. Se accessKey/secretKey estiverem preenchidos, usa credenciais estáticas;
     * caso contrário, usa DefaultAWSCredentialsProviderChain.
     */
    @Bean
    public AmazonS3 amazonS3() {
        AmazonS3ClientBuilder builder = AmazonS3ClientBuilder.standard();

        // Se usuário especificou access-key e secret-key em aws.properties, usa BasicAWSCredentials
        if (accessKey != null && secretKey != null) {
            AWSCredentials creds = new BasicAWSCredentials(accessKey, secretKey);
            builder
                .withCredentials(new AWSStaticCredentialsProvider(creds))
                .withRegion(Regions.fromName(awsRegion));
        } else {
            // Usa DefaultAWSCredentialsProviderChain (variáveis de ambiente, ~/.aws/credentials, IAM Role, etc.)
            builder
                .withCredentials(DefaultAWSCredentialsProviderChain.getInstance())
                .withRegion(Regions.fromName(awsRegion));
        }

        return builder.build();
    }

    /**
     * Injetável do nome do bucket (bean String).
     * Para que o controller possa saber em qual bucket operar.
     */
    @Bean
    public String bucketName() {
        return bucketName;
    }
}
