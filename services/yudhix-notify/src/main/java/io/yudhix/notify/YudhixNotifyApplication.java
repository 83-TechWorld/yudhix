package io.yudhix.notify;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.notify", "io.yudhix.common"})
public class YudhixNotifyApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixNotifyApplication.class, args);
    }
}
