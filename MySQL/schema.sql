--
-- PostgreSQL database dump
--

\restrict kchn2mGil4IZImMR6AtEImsw9RIEM8ekQAK3Ekm9iCLyqsVVxOmVj6gA3prCBc4

-- Dumped from database version 17.7 (Debian 17.7-3.pgdg13+1)
-- Dumped by pg_dump version 17.7 (Debian 17.7-3.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: chatmessage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatmessage (
    content character varying NOT NULL,
    role character varying(50) NOT NULL,
    id uuid NOT NULL,
    owner_id uuid NOT NULL,
    session_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.chatmessage OWNER TO postgres;

--
-- Name: chatsession; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatsession (
    title character varying(255) NOT NULL,
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.chatsession OWNER TO postgres;

--
-- Name: crawl_index; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crawl_index (
    url_hash character varying(64) NOT NULL,
    original_url character varying(2048) NOT NULL,
    file_path character varying(512) NOT NULL,
    content_md5 character varying(64) NOT NULL,
    content_type character varying(128),
    size_bytes integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.crawl_index OWNER TO postgres;

--
-- Name: crawler_task; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crawler_task (
    id uuid NOT NULL,
    status character varying NOT NULL,
    result_sql_content character varying,
    created_at timestamp without time zone NOT NULL,
    pipeline_state character varying,
    current_phase character varying
);


ALTER TABLE public.crawler_task OWNER TO postgres;

--
-- Name: industrial_batch; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.industrial_batch (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    url character varying NOT NULL,
    item_count integer NOT NULL,
    status character varying NOT NULL,
    storage_path character varying
);


ALTER TABLE public.industrial_batch OWNER TO postgres;

--
-- Name: item; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.item (
    description character varying(255),
    title character varying(255) NOT NULL,
    id uuid NOT NULL,
    owner_id uuid NOT NULL
);


ALTER TABLE public.item OWNER TO postgres;

--
-- Name: user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."user" (
    email character varying(255) NOT NULL,
    is_active boolean NOT NULL,
    is_superuser boolean NOT NULL,
    full_name character varying(255),
    hashed_password character varying NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public."user" OWNER TO postgres;

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: chatmessage chatmessage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatmessage
    ADD CONSTRAINT chatmessage_pkey PRIMARY KEY (id);


--
-- Name: chatsession chatsession_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatsession
    ADD CONSTRAINT chatsession_pkey PRIMARY KEY (id);


--
-- Name: crawl_index crawl_index_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_index
    ADD CONSTRAINT crawl_index_pkey PRIMARY KEY (url_hash);


--
-- Name: crawler_task crawler_task_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawler_task
    ADD CONSTRAINT crawler_task_pkey PRIMARY KEY (id);


--
-- Name: industrial_batch industrial_batch_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.industrial_batch
    ADD CONSTRAINT industrial_batch_pkey PRIMARY KEY (id);


--
-- Name: item item_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.item
    ADD CONSTRAINT item_pkey PRIMARY KEY (id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: ix_crawl_index_content_md5; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_crawl_index_content_md5 ON public.crawl_index USING btree (content_md5);


--
-- Name: ix_crawl_index_url_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_crawl_index_url_hash ON public.crawl_index USING btree (url_hash);


--
-- Name: ix_user_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_user_email ON public."user" USING btree (email);


--
-- Name: chatmessage chatmessage_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatmessage
    ADD CONSTRAINT chatmessage_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public."user"(id);


--
-- Name: chatmessage chatmessage_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatmessage
    ADD CONSTRAINT chatmessage_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.chatsession(id) ON DELETE CASCADE;


--
-- Name: chatsession chatsession_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatsession
    ADD CONSTRAINT chatsession_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: item item_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.item
    ADD CONSTRAINT item_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict kchn2mGil4IZImMR6AtEImsw9RIEM8ekQAK3Ekm9iCLyqsVVxOmVj6gA3prCBc4

