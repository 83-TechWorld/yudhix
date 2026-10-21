package io.yudhix.meter;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.meter", "io.yudhix.common"})
public class YudhixMeterApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixMeterApplication.class, args);
    }
}
