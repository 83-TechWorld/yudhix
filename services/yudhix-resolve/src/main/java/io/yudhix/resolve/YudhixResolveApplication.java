package io.yudhix.resolve;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.resolve", "io.yudhix.common"})
public class YudhixResolveApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixResolveApplication.class, args);
    }
}
