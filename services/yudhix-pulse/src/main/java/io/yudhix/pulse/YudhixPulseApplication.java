package io.yudhix.pulse;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.pulse", "io.yudhix.common"})
public class YudhixPulseApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixPulseApplication.class, args);
    }
}
