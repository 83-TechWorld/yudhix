package io.yudhix.catalog;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.catalog", "io.yudhix.common"})
public class YudhixCatalogApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixCatalogApplication.class, args);
    }
}
