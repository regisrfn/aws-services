import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.auth.credentials.AwsCredentialsProvider;
import software.amazon.awssdk.auth.credentials.AwsCredentialsProviderChain;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.sqs.SqsClient;

@Configuration
public class AwsConfig {

    @Value("${AWS_REGION:us-east-1}")
    private String awsRegion;

    @Value("${AWS_ASSUME_ROLE}")
    private String assumeRoleArn;

    @Bean
    public S3Client s3Client() {
        S3Client.Builder builder = S3Client.builder().region(Region.of(awsRegion));
        configureCredentials(builder);
        return builder.build();
    }

    @Bean
    public SqsClient sqsClient() {
        SqsClient.Builder builder = SqsClient.builder().region(Region.of(awsRegion));
        configureCredentials(builder);
        return builder.build();
    }

    private void configureCredentials(AwsCredentialsProvider.Builder builder) {
        if (assumeRoleArn != null && !assumeRoleArn.isEmpty()) {
            builder.credentialsProvider(
                AwsCredentialsProviderChain.builder()
                    .credentialsProviders(
                        DefaultCredentialsProvider.create(),
                        WebIdentityTokenFileCredentialsProvider.create()
                    )
                    .build()
            );
        }
    }
}
