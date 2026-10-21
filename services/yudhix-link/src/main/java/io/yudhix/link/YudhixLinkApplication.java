package io.yudhix.link;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.link", "io.yudhix.common"})
public class YudhixLinkApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixLinkApplication.class, args);
    }
}
