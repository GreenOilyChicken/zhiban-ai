package com.zhiban.ai.config;

import com.zhiban.ai.security.JwtAuthenticationFilter;
import com.zhiban.ai.security.JwtTokenProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

/**
 * Spring Security 安全配置
 * - JWT 无状态认证
 * - 方法级别权限控制（@PreAuthorize）
 *
 * @author zhiban
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true)
public class SecurityConfig {

    private final JwtTokenProvider jwtTokenProvider;

    public SecurityConfig(JwtTokenProvider jwtTokenProvider) {
        this.jwtTokenProvider = jwtTokenProvider;
    }

    /**
     * 密码加密器
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    /**
     * 认证管理器
     */
    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }

    /**
     * CORS 跨域配置
     */
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOriginPatterns(List.of("*"));
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("*"));
        configuration.setAllowCredentials(true);
        configuration.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    /**
     * 安全过滤链
     */
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                // 公开接口（附件一 §3.1：游客登录、手机号登录无需凭证）
                //
                // 注意：server.servlet.context-path=/api 已被 Servlet 容器剥离，
                // 因此此处匹配的是「去掉 /api 前缀」后的路径。
                .requestMatchers(
                    "/auth/login",
                    "/auth/register",
                    "/auth/guest-login",
                    "/auth/phone-login",
                    "/auth/sms-code",
                    "/auth/refresh"
                ).permitAll()
                .requestMatchers("/help/articles", "/help/article/**").permitAll()
                .requestMatchers("/help/gov-policy", "/help/gov-policy/**").permitAll()
                .requestMatchers("/help/categories").permitAll()
                .requestMatchers("/help/faq").permitAll()
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers("/error").permitAll()
                // WebSocket 握手由 ChatWebSocketHandler 自行处理鉴权
                .requestMatchers("/ws/**").permitAll()
                // 管理员接口需要 ADMIN 角色（同时由 @PreAuthorize 在方法级二次校验）
                .requestMatchers("/admin/**").hasRole("ADMIN")
                // 其余请求需要认证
                .anyRequest().authenticated()
            )
            .addFilterBefore(
                new JwtAuthenticationFilter(jwtTokenProvider),
                UsernamePasswordAuthenticationFilter.class
            );

        return http.build();
    }
}
