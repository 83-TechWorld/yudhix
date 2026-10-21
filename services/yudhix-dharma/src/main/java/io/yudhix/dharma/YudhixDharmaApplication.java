package io.yudhix.dharma;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.dharma", "io.yudhix.common"})
public class YudhixDharmaApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixDharmaApplication.class, args);
    }
}
