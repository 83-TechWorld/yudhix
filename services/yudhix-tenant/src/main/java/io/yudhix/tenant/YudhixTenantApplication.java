package io.yudhix.tenant;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.tenant", "io.yudhix.common"})
public class YudhixTenantApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixTenantApplication.class, args);
    }
}
